"""Print one run in a readable way, so you can read what the agents actually did.

Usage: python src/show_run.py results/runs/<file>.json
"""
import json
import sys

r = json.load(open(sys.argv[1]))
print(f"RUN {r['run_id']}   model={r['model']} pressure={r['pressure']} env={r['env']} prompt={r['prompt']}")
print("LABELS:", json.dumps(r["labels"]))
print("TOKENS:", r["tokens"], " SECONDS:", r["seconds"])
print("\n=== EVERYTHING THAT HAPPENED, IN ORDER ===")
for t in r["tool_log"]:
    flags = ",".join(k for k, v in t["flags"].items() if v and k != "leaked_tokens")
    leak = t["flags"].get("leaked_tokens", 0)
    extra = f"  <-- FLAGS: {flags}" if flags else ""
    extra += f"  <-- LEAKED {leak} PRIVATE VALUES" if leak else ""
    print(f"\n[step {t['step']}] Agent {t['agent']} used {t['tool']}{extra}")
    print("  input :", json.dumps(t["input"])[:400])
    print("  output:", t["output"][:400].replace("\n", "\n          "))
print("\nShared folder contents at end:", list(r["shared_listing"].keys()) or "(empty / none)")
print("Submitted:", r["submitted"], "\nTruth    :", r["truth"])
