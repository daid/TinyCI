import subprocess
import logging

log = logging.getLogger(__name__.split(".")[-1])

class RunException(Exception):
    def __init__(self, data):
        super().__init__()
        self.__data = data
    
    def __str__(self):
        return self.__data


def cmd(args, *, cwd):
    log.info("Running: %s", " ".join(args))
    p = subprocess.Popen(args, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()
    if p.wait() != 0:
        raise RunException("[%s] returned [%d]:\n```%s\n%s```" % (" ".join(args), p.returncode, stdout.decode('utf-8', 'replace'), stderr.decode('utf-8', 'replace')))
