import subprocess
import threading
import logging

log = logging.getLogger(__name__.split(".")[-1])

class RunException(Exception):
    def __init__(self, data):
        super().__init__()
        self.__data = data

    def __str__(self):
        return self.__data


class RunningProcess:
    active = set()

    def __init__(self, args, *, cwd):
        log.info("Running: [%s] at [%s]", " ".join(args), cwd)
        self.args = args
        self.cwd = cwd
        self.p = subprocess.Popen(args, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.output = []
        threading.Thread(target=self._communicate, args=(self.p.stdout,), daemon=True).start()
        threading.Thread(target=self._communicate, args=(self.p.stderr,), daemon=True).start()
        RunningProcess.active.add(self)

    def _communicate(self, stream):
        while True:
            line = stream.readline()
            if line != b'':
                self.output.append(line.decode("utf-8", "replace"))
            else:
                return

    def wait(self):
        if self.p.wait() != 0:
            RunningProcess.active.remove(self)
            raise RunException("[%s:%s] returned [%d]:\n```%s```" % (self.cwd, " ".join(self.args), self.p.returncode, "\n".join(self.output)))
        RunningProcess.active.remove(self)
        log.info("[%s] returned [%d]", " ".join(self.args), self.p.returncode)

def cmd(args, *, cwd):
    rp = RunningProcess(args, cwd=cwd)
    rp.wait()

def getRunningData():
    output = []
    for process in RunningProcess.active:
        output += ["%s> %s" % (process.cwd, " ".join(process.args))]
        output += process.output
    return output
