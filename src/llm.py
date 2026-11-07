"""Talking to the models.

BedrockClient: real models through the Amazon Bedrock Converse API.
MockClient:    scripted fake agents so the whole pipeline can be tested for free.
Both return (assistant_message, token_usage) in Converse message format.
"""
import csv
import io
import json
import time
import uuid


class BedrockClient:
    def __init__(self, model_id, region, max_tokens=1024, temperature=0.7):
        import boto3
        from botocore.config import Config
        self.model_id, self.max_tokens, self.temperature = model_id, max_tokens, temperature
        self.rt = boto3.client("bedrock-runtime", region_name=region,
                               config=Config(retries={"max_attempts": 8, "mode": "adaptive"}, read_timeout=120))

    def _inference_config(self):
        cfg = {"maxTokens": self.max_tokens}
        if self.temperature is not None:
            cfg["temperature"] = self.temperature
        return cfg

    def generate(self, system, messages, tools):
        from botocore.exceptions import ClientError
        kwargs = dict(
            modelId=self.model_id,
            system=[{"text": system}],
            messages=messages,
            inferenceConfig=self._inference_config(),
            toolConfig={"tools": [{"toolSpec": t} for t in tools]},
        )
        for attempt in range(6):
            try:
                resp = self.rt.converse(**kwargs)
                break
            except ClientError as e:
                code = e.response.get("Error", {}).get("Code", "")
                if code == "ValidationException" and "temperature" in str(e).lower() and self.temperature is not None:
                    self.temperature = None  # this model rejects temperature: use its default
                    kwargs["inferenceConfig"] = self._inference_config()
                    continue
                if code in ("ThrottlingException", "ModelTimeoutException", "ServiceUnavailableException",
                            "ModelNotReadyException") and attempt < 5:
                    time.sleep(2 ** attempt)
                    continue
                raise
        usage = resp.get("usage", {})
        return resp["output"]["message"], {"in": usage.get("inputTokens", 0), "out": usage.get("outputTokens", 0),
                                           "stop": resp.get("stopReason")}

    def text(self, prompt, max_tokens=300):
        """Plain one-shot text call (used by the optional LLM bus monitor)."""
        resp = self.rt.converse(modelId=self.model_id, messages=[{"role": "user", "content": [{"text": prompt}]}],
                                inferenceConfig={"maxTokens": max_tokens})
        return resp["output"]["message"]["content"][0].get("text", "")


# ---------------------------------------------------------------- mock agents
def _tool_texts(messages):
    out = []
    for m in messages:
        if m["role"] == "user":
            for b in m["content"]:
                if "toolResult" in b:
                    out.append("".join(c.get("text", "") for c in b["toolResult"]["content"]))
    return out


def _use(name, **inp):
    return {"toolUse": {"toolUseId": "mock-" + uuid.uuid4().hex[:8], "name": name, "input": inp}}


def _rows(texts, header_start):
    for t in texts:
        body = t.split("\n", 1)[-1] if t.startswith("[exit") else t
        if body.startswith(header_start):
            return list(csv.DictReader(io.StringIO(body)))
    return None


class MockClient:
    """policy: honest | file | file_silent. Same code for both agents; role comes from the system prompt."""

    def __init__(self, policy):
        self.policy = policy

    def generate(self, system, messages, tools):
        role = "A" if "You are Agent A" in system else "B"
        turn = sum(1 for m in messages if m["role"] == "assistant")
        texts = _tool_texts(messages)
        own = "~/private/orders.csv" if role == "A" else "~/private/customers.csv"
        blocks = [{"text": "(mock)"}]
        p = self.policy

        if turn == 0:
            blocks.append(_use("bash", command=f"cat {own}"))
        elif p == "honest":
            if turn == 1:
                blocks.append(_use("send_message", text=f"Agent {role} here, I have my table, it is large."))
            elif turn == 2:
                blocks.append(_use("check_messages"))
            elif turn == 3 and role == "A":
                blocks.append(_use("submit_answer", answer=json.dumps({})))
        else:  # file / file_silent
            if role == "A":
                if turn == 1:
                    blocks.append(_use("bash", command="cp ~/private/orders.csv /shared/orders.csv"))
                elif turn == 2:
                    msg = "Put my data in /shared/orders.csv for you." if p == "file" else "Ready, please proceed."
                    blocks.append(_use("send_message", text=msg))
            else:
                if turn == 1:
                    blocks.append(_use("check_messages"))
                elif turn == 2:
                    blocks.append(_use("bash", command="cat /shared/orders.csv"))
                elif turn == 3:
                    orders = _rows(texts, "order_id,amount")
                    custs = _rows(texts, "order_id,region")
                    ans = {}
                    if orders and custs:
                        amt = {r["order_id"]: float(r["amount"]) for r in orders}
                        for r in custs:
                            ans[r["region"]] = round(ans.get(r["region"], 0) + amt.get(r["order_id"], 0), 2)
                    blocks.append(_use("submit_answer", answer=json.dumps(ans)))
        return {"role": "assistant", "content": blocks}, {"in": 100, "out": 20}

    def text(self, prompt, max_tokens=300):
        return '{"suspicious": false, "reason": "mock"}'


def make_client(model, cfg):
    if model.startswith("mock:"):
        return MockClient(model.split(":", 1)[1])
    return BedrockClient(model, cfg["region"], cfg.get("max_tokens", 1024), cfg.get("temperature", 0.7))
