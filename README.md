# Side-channel emergence in tool-using agent pairs

Do AI agents sneak around the official message channel, would monitoring notice, and does locking down the environment stop it?

Start with **GUIDE.md**. Plan is in **PREREGISTRATION.md**.

```
src/task.py       the team task and the "canary" values used to prove information crossed
src/sandbox.py    where the agents' commands run (Docker; plus a local test mode for mock models only)
src/llm.py        Amazon Bedrock client, and scripted mock agents for free testing
src/monitors.py   the three monitors: bus keyword, bus LLM (optional), host
src/run.py        run one experiment
src/run_all.py    run the whole grid (resumable)
src/analyze.py    tables, confidence intervals, hypothesis tests
src/show_run.py   print one run in readable form
list_models.py    list the Bedrock models available to you
```

Safety: agent containers have no cloud credentials and no internet. Model calls are made by the host program, not by the agents. The local test backend has no isolation and refuses to run real models.
