import os, sys

def sub(path, old, new):
    s = open(path).read()
    if new in s:
        print("already patched:", os.path.basename(path))
        return
    assert s.count(old) == 1, f"pattern not found once in {path}: {old[:70]!r} (found {s.count(old)})"
    open(path, "w").write(s.replace(old, new))
    print("patched:", os.path.basename(path))

root = sys.argv[1] if len(sys.argv) > 1 else "."
M = os.path.join(root, "src", "monitors.py")
sub(M, 'r"/shared", r"\\bnc\\b",',
    'r"/shared/\\S", r"\\b(cp|mv|tee|rsync|scp|install|ln)\\b[^;|&\\n]*\\s/shared\\b", r">\\s*/shared", r"\\bnc\\b",')
sub(M, 'r"/etc/hosts", ', 'r"/shared\\b", r"/etc/hosts", ')
print("DONE")
