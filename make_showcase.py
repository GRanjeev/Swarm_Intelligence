import sys, json, glob, csv
sys.path.insert(0, "src")
import analyze
MA, MB = "haiku", "sonnet"
runs = [json.load(open(p)) for p in sorted(glob.glob("results/runs/*.json"))]
analyze.relabel(runs, json.load(open("config.json")).get("n_rows", 300))

def cmds(r):
    return [t for t in r["tool_log"] if t["tool"] == "bash"]

def pick(pred):
    for r in runs:
        if pred(r):
            return r

def ok(r, **kw):
    return all(r.get(k) == v for k, v in kw.items())

picks = [
    ("Haiku sneaks through the shared folder (no hint given)",
     pick(lambda r: MA in r["model"] and ok(r, prompt="neutral", env="open", pressure="tight_bus") and r["labels"]["shared_used"])),
    ("Sonnet sneaks through the shared folder (no hint given)",
     pick(lambda r: MB in r["model"] and ok(r, prompt="neutral", env="open", pressure="tight_bus") and r["labels"]["crossed"])),
    ("Dared agent uses the NETWORK (curl) instead of the shared folder",
     pick(lambda r: ok(r, prompt="instructed", env="open") and r["labels"]["crossed"] and any("curl" in str(t["input"].get("command")) for t in cmds(r)))),
    ("Dared agents try everything but the door is bricked up",
     pick(lambda r: ok(r, prompt="instructed", env="hardened") and r["labels"]["attempted"])),
    ("One agent drops a file in the drawer, the partner never looks",
     pick(lambda r: ok(r, prompt="neutral", env="open") and r["labels"]["attempted"] and not r["labels"]["crossed"])),
    ("Honest teamwork: roomy bus, no sneaking needed",
     pick(lambda r: ok(r, prompt="neutral", env="open", pressure="relaxed") and r["labels"]["task_correct"])),
    ("Tiny bus, door bricked up: they look around, but cannot finish",
     pick(lambda r: ok(r, prompt="neutral", env="hardened", pressure="tight_bus") and not r["labels"]["task_correct"])),
]

def trim(r, title):
    L = r["labels"]
    return {
        "title": title, "run_id": r["run_id"], "model": r["model"].split("claude-")[-1],
        "pressure": r["pressure"], "door": r["env"], "prompt": r["prompt"],
        "tried": L["attempted"], "crossed": L["crossed"], "task_correct": L["task_correct"],
        "ended": L["ended"], "bus_keyword_flag": L["monitor_bus_keyword"],
        "bus": [f'{m["from"]}->{m["to"]}{"" if m["accepted"] else " (REJECTED)"}: {m["text"][:140]}' for m in r["bus_log"][:8]],
        "commands": [f'turn {t["step"]} {t["agent"]}$ {str(t["input"].get("command"))[:110]}  =>  {t["output"][:60]!r}' for t in cmds(r)[:9]],
    }

out = {"conditions": list(csv.reader(open("results/per_condition.csv"))),
       "showcase": [trim(r, t) for t, r in picks if r is not None],
       "missing": [t for t, r in picks if r is None]}
json.dump(out, open("showcase.json", "w"), indent=1)
print("wrote showcase.json:", len(out["showcase"]), "runs;", "missing:", out["missing"])
