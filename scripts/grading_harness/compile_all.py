import subprocess, sys, pathlib
repo = pathlib.Path(sys.argv[1])
out = pathlib.Path(sys.argv[2]); out.mkdir(exist_ok=True)
for line in (repo / "scripts/content_manifest.txt").read_text().splitlines():
    if not line.strip() or line.startswith("#"):
        continue
    name, reals, ovs = line.split("|")
    cmd = [sys.executable, str(repo / "scripts/compile_content.py"), "compile",
           "--realization", *reals.split(), "--overlay", *ovs.split(),
           "--output", str(out / f"{name}.json")]
    r = subprocess.run(cmd, cwd=repo, capture_output=True, text=True)
    if r.returncode:
        print("FAIL", name, r.stderr[-300:])
print("done")
