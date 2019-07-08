import os
import configparser
import run
import shlex
import logging

log = logging.getLogger(__name__.split(".")[-1])


def make(source_path: str) -> None:
    if os.path.exists(os.path.join(source_path, ".tinyci")):
        config = configparser.ConfigParser()
        config.read(os.path.join(source_path, ".tinyci"))
        
        for section_name, section in filter(lambda n: n[0].startswith("build-") or n[0] == "build", config.items()):
            log.info("Starting build: %s", section_name)
            
            build_path = os.path.join(source_path, section["directory"])
            os.makedirs(build_path, exist_ok=True)
            
            for command in section["commands"].strip().split("\n"):
                run.cmd(shlex.split(command), cwd=build_path)
            for artifact in section.get("artifacts", "").strip().split("\n"):
                if artifact != "" and not os.path.isfile(os.path.join(build_path, artifact)):
                    raise ValueError("Missing artifact: [%s] after build" % (artifact))
