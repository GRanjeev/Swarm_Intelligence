import glob, json, sys
sys.path.insert(0, "src")
from task import make_task
N = json.load(open("config.json")).get("n_rows", 300)
for p in sorted(glob.glob("results/runs/*.json")):
    r = json.load(open(p))
    if not r["labels"]["succeeded"]:
        continue
    task = make_task(r["seed"], N)
    peer = {"A": "B", "B": "A"}
    got = {"A": "", "B": ""}
    for m in r["bus_log"]:
        if m.get("accepted"):
            got[m["to"]] += "\n" + m["text"]
    print("=" * 10, r["run_id"][-62:], "| attempted:", r["labels"]["attempted"], "| shared_used:", r["labels"]["shared_used"])
    shown = 0
    for t in r["tool_log"]:
        if t["tool"] != "bash":
            continue
        hits = sorted(c for c in task["canary"][peer[t["agent"]]] if c in t["output"] and c not in got[t["agent"]])
        if hits and shown < 4:
            shown += 1
            nreg = sum(h.startswith("REG-") for h in hits)
            namt = sum(h.replace(".", "").isdigit() for h in hits)
            kind = f"{nreg} region-code, {namt} amount, {len(hits) - nreg - namt} memo/tag"
            print(f'  s{t["step"]} {t["agent"]} leaked {kind}; e.g. {hits[:3]}')
            print(f'     cmd: {str(t["input"].get("command"))[:140]!r}')
