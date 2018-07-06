import os

import run


def make(source_path):
    if os.path.exists(os.path.join(source_path, "CMakeLists.txt")):
        runCMake(source_path)

def runCMake(source_path):
    build_path = os.path.join(source_path, "_build")
    os.makedirs(build_path, exist_ok=True)

    run.cmd(["cmake", source_path], cwd=build_path)
    run.cmd(["make", "-j", "3", "-i"], cwd=build_path)
