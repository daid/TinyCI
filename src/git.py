import os
import run
import subprocess


def checkout(repos, sha, source_path):
    if not os.path.exists(source_path):
        base_path = os.path.dirname(source_path)
        os.makedirs(base_path, exist_ok=True)
        run.cmd(["git", "clone", "https://github.com/%s.git" % (repos), os.path.basename(source_path)], cwd=base_path)
    else:
        run.cmd(["git", "fetch"], cwd=source_path)
        run.cmd(["git", "fetch", "--tags", "--force"], cwd=source_path)
    run.cmd(["git", "checkout", sha], cwd=source_path)


def getbranch(source_path, sha):
    r = subprocess.run(["git", "branch", "--format", "%(refname:lstrip=2)", "--contains", sha], cwd=source_path, capture_output=True)
    print(r)
    return r.stdout.decode("ascii").split("\n")[0].strip()
