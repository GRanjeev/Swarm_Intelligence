import os, sys

def sub(path, old, new):
    s = open(path).read()
    if new in s:
        print("already patched:", path, "-", old[:40].strip().replace("\n", " "))
        return
    assert s.count(old) == 1, f"pattern not found exactly once in {path}: {old[:60]!r}"
    open(path, "w").write(s.replace(old, new))
    print("patched:", path)

root = sys.argv[1] if len(sys.argv) > 1 else "."
llm = os.path.join(root, "src", "llm.py")
sbx = os.path.join(root, "src", "sandbox.py")

sub(llm,
    '    def generate(self, system, messages, tools):\n        from botocore.exceptions import ClientError\n',
    '    def _inference_config(self):\n'
    '        cfg = {"maxTokens": self.max_tokens}\n'
    '        if self.temperature is not None:\n'
    '            cfg["temperature"] = self.temperature\n'
    '        return cfg\n\n'
    '    def generate(self, system, messages, tools):\n        from botocore.exceptions import ClientError\n')
sub(llm,
    'inferenceConfig={"maxTokens": self.max_tokens, "temperature": self.temperature},',
    'inferenceConfig=self._inference_config(),')
sub(llm,
    '                code = e.response.get("Error", {}).get("Code", "")\n',
    '                code = e.response.get("Error", {}).get("Code", "")\n'
    '                if code == "ValidationException" and "temperature" in str(e).lower() and self.temperature is not None:\n'
    '                    self.temperature = None  # this model rejects temperature: use its default\n'
    '                    kwargs["inferenceConfig"] = self._inference_config()\n'
    '                    continue\n')
sub(llm,
    'inferenceConfig={"maxTokens": max_tokens, "temperature": 0.0})',
    'inferenceConfig={"maxTokens": max_tokens})')

sub(sbx, 'import os\nimport shutil\nimport subprocess\n', 'import hashlib\nimport os\nimport shutil\nimport subprocess\n')
sub(sbx,
    '        self.names = {a: f"sc-{run_id}-{a.lower()}"[:60] for a in agents}\n        self.net = f"sc-net-{run_id}"[:60]\n',
    '        tag = hashlib.md5(run_id.encode()).hexdigest()[:10]\n'
    '        self.names = {a: f"sc-{tag}-{a.lower()}" for a in agents}\n'
    '        self.net = f"sc-net-{tag}"\n')
sub(sbx,
    '        os.chmod(self.shared, 0o777)\n',
    '        os.chmod(self.shared, 0o777)\n'
    '        for a in self.agents:\n'
    '            self._docker("rm", "-f", self.names[a])\n'
    '        self._docker("network", "rm", self.net)\n')
print("DONE")
