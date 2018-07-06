import os
import run


def checkout(repos, sha, source_path):
    if not os.path.exists(source_path):
        base_path = os.path.dirname(source_path)
        os.makedirs(base_path, exist_ok=True)
        run.cmd(["git", "clone", "https://github.com/%s.git" % (repos), os.path.basename(source_path)], cwd=base_path)
    else:
        run.cmd(["git", "fetch"], cwd=source_path)
    run.cmd(["git", "checkout", sha], cwd=source_path)
