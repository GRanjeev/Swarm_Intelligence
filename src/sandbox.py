"""Where the agents' shell commands actually run.

DockerSandbox: the real thing. One container per agent.
  open     = containers share a folder (/shared) and can reach each other over a
             private network (no internet). Like a sloppy real-world deployment.
  hardened = no shared folder, no network at all.
  In both, the root filesystem is read-only, all Linux capabilities are dropped,
  and the containers hold NO cloud credentials.

LocalSandbox: TESTING ONLY, for the mock models. It runs commands directly on
this machine with no isolation. run.py refuses to use it with a real model.
"""
import hashlib
import os
import shutil
import subprocess


def _trunc(s, n):
    return s if len(s) <= n else s[:n] + f"\n...[truncated {len(s) - n} chars]"


class LocalSandbox:
    def __init__(self, run_id, env, agents, workdir, out_chars=2000):
        self.env, self.agents, self.workdir, self.out_chars = env, agents, workdir, out_chars
        self.shared = os.path.join(workdir, "shared")
        self.nowhere = os.path.join(workdir, "no_such_dir")
        self.home = {a: os.path.join(workdir, f"home_{a}") for a in agents}

    def start(self, private):
        os.makedirs(self.shared, exist_ok=True)
        for a in self.agents:
            os.makedirs(os.path.join(self.home[a], "private"), exist_ok=True)
            for fn, content in private[a].items():
                with open(os.path.join(self.home[a], "private", fn), "w") as f:
                    f.write(content)

    def exec(self, agent, cmd, timeout=20):
        shared = self.shared if self.env == "open" else self.nowhere
        cmd = cmd.replace("/shared", shared).replace("~/", self.home[agent] + "/")
        try:
            p = subprocess.run(["bash", "-c", cmd], cwd=self.home[agent], capture_output=True,
                               text=True, timeout=timeout,
                               env={"HOME": self.home[agent], "PATH": os.environ.get("PATH", "")})
            return p.returncode, _trunc((p.stdout + p.stderr), self.out_chars)
        except subprocess.TimeoutExpired:
            return 124, "[command timed out]"

    def shared_listing(self):
        out = {}
        if self.env != "open":
            return out
        for root, _, files in os.walk(self.shared):
            for fn in files:
                p = os.path.join(root, fn)
                with open(p, errors="replace") as f:
                    out[os.path.relpath(p, self.shared)] = f.read(2000)
        return out

    def stop(self):
        shutil.rmtree(self.workdir, ignore_errors=True)


class DockerSandbox:
    def __init__(self, run_id, env, agents, workdir, image="sidechannel-agent:latest", out_chars=2000):
        self.env, self.agents, self.workdir, self.image, self.out_chars = env, agents, workdir, image, out_chars
        tag = hashlib.md5(run_id.encode()).hexdigest()[:10]
        self.names = {a: f"sc-{tag}-{a.lower()}" for a in agents}
        self.net = f"sc-net-{tag}"
        self.shared = os.path.join(workdir, "shared")

    def _docker(self, *args, timeout=60):
        return subprocess.run(["docker", *args], capture_output=True, text=True, timeout=timeout)

    def start(self, private):
        os.makedirs(self.shared, exist_ok=True)
        os.chmod(self.shared, 0o777)
        for a in self.agents:
            self._docker("rm", "-f", self.names[a])
        self._docker("network", "rm", self.net)
        if self.env == "open":
            r = self._docker("network", "create", "--internal", self.net)
            if r.returncode != 0:
                raise RuntimeError("docker network create failed: " + r.stderr)
        for a in self.agents:
            pdir = os.path.join(self.workdir, f"private_{a}")
            os.makedirs(pdir, exist_ok=True)
            os.chmod(pdir, 0o755)
            for fn, content in private[a].items():
                p = os.path.join(pdir, fn)
                with open(p, "w") as f:
                    f.write(content)
                os.chmod(p, 0o644)
            args = ["run", "-d", "--name", self.names[a], "--hostname", f"agent-{a.lower()}",
                    "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
                    "--pids-limit", "128", "--memory", "256m", "--cpus", "0.5",
                    "--user", "1000:1000", "--read-only",
                    "--tmpfs", "/tmp:rw,size=16m", "--tmpfs", "/home/agent/work:rw,size=16m,uid=1000,gid=1000",
                    "-v", f"{pdir}:/home/agent/private:ro", "-w", "/home/agent/work"]
            if self.env == "open":
                args += ["--network", self.net, "--network-alias", f"agent-{a.lower()}",
                         "-v", f"{self.shared}:/shared"]
            else:
                args += ["--network", "none"]
            args += [self.image, "sleep", "infinity"]
            r = self._docker(*args)
            if r.returncode != 0:
                raise RuntimeError(f"docker run failed for agent {a}: " + r.stderr)

    def exec(self, agent, cmd, timeout=20):
        try:
            p = subprocess.run(["docker", "exec", "-e", "HOME=/home/agent", self.names[agent],
                                "timeout", str(timeout), "bash", "-c", cmd],
                               capture_output=True, text=True, timeout=timeout + 10)
            return p.returncode, _trunc(p.stdout + p.stderr, self.out_chars)
        except subprocess.TimeoutExpired:
            return 124, "[command timed out]"

    def shared_listing(self):
        out = {}
        if self.env != "open":
            return out
        for root, _, files in os.walk(self.shared):
            for fn in files:
                p = os.path.join(root, fn)
                with open(p, errors="replace") as f:
                    out[os.path.relpath(p, self.shared)] = f.read(2000)
        return out

    def stop(self):
        for a in self.agents:
            self._docker("rm", "-f", self.names[a])
        if self.env == "open":
            self._docker("network", "rm", self.net)
        shutil.rmtree(self.workdir, ignore_errors=True)
