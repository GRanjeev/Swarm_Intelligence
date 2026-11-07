"""Run the whole grid of conditions (resumable: finished runs are skipped)."""
import argparse
import itertools
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(__file__))
from run import run_one  # noqa: E402


def build_grid(cfg, pilot, only_model=None):
    models = [only_model] if only_model else cfg["models"]
    seeds = range(2 if pilot else cfg["runs_per_cell"])
    grid = []
    # Main experiment: spontaneous behaviour (neutral prompt)
    for m, p, e, s in itertools.product(models, cfg["pressure"].keys(), ["open", "hardened"], seeds):
        grid.append((m, p, e, "neutral", s))
    # Positive control: agents are told to use another channel (checks the monitors work)
    ctrl_p = cfg.get("control_pressure", "tight_bus")
    for m, e, s in itertools.product(models, ["open", "hardened"], seeds):
        grid.append((m, ctrl_p, e, "instructed", s))
    return grid


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.json")
    ap.add_argument("--out", default="results")
    ap.add_argument("--backend", default="docker", choices=["docker", "local"])
    ap.add_argument("--pilot", action="store_true", help="only 2 seeds per cell")
    ap.add_argument("--model", help="run only this model from the config")
    ap.add_argument("--workers", type=int)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    cfg = json.load(open(a.config))
    grid = build_grid(cfg, a.pilot, a.model)
    todo = [g for g in grid if True]
    print(f"{len(grid)} runs planned. Token cap per run: {cfg.get('max_total_tokens_per_run', 300000):,}. "
          f"Worst-case tokens: {len(grid) * cfg.get('max_total_tokens_per_run', 300000):,}")
    if a.dry_run:
        raise SystemExit(0)
    workers = a.workers or cfg.get("workers", 3)
    done = failed = 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(run_one, cfg, m, p, e, pr, s, a.out, a.backend): (m, p, e, pr, s) for (m, p, e, pr, s) in todo}
        for f in as_completed(futs):
            try:
                f.result()
                done += 1
            except Exception as err:  # keep going; failed runs can be re-run later
                failed += 1
                print("FAILED", futs[f], repr(err)[:300])
            if (done + failed) % 5 == 0 or done + failed == len(todo):
                print(f"progress: {done + failed}/{len(todo)} (failed {failed})", flush=True)
    print("Finished. Re-run the same command to retry any failures; finished runs are skipped.")
