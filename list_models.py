"""Print the Bedrock models you can call from your region, and which ones support tool use.

Usage:  python list_models.py us-east-1
Copy the 'ID' of the models you want into config.json -> "models".
If an inference-profile ID (starts with us./eu./apac.) is listed for a model, use that one.
"""
import sys

import boto3

region = sys.argv[1] if len(sys.argv) > 1 else "us-east-1"
b = boto3.client("bedrock", region_name=region)

print(f"Region: {region}\n")
print("== Foundation models (text output, on-demand or profile) ==")
for m in b.list_foundation_models(byOutputModality="TEXT")["modelSummaries"]:
    if m.get("modelLifecycle", {}).get("status") == "ACTIVE":
        print(f"{m['modelId']:70s} {m['providerName']}")

print("\n== Inference profiles (use these IDs if the plain model ID gives an error) ==")
try:
    for p in b.list_inference_profiles()["inferenceProfileSummaries"]:
        print(f"{p['inferenceProfileId']:70s} {p['inferenceProfileName']}")
except Exception as e:  # noqa
    print("(could not list inference profiles:", e, ")")

print("\nNeed tool use support. Check the Bedrock docs page 'Supported models and model features' (Converse API > Tool use).")
