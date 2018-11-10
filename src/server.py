import flask
import stat
import os
import logging
import json
import requests
import threading
import queue
import subprocess

import config
import git
import github
import hmac
import hashlib
import build

log = logging.getLogger(__name__.split(".")[-1])


class TinyCIServer(flask.Flask):
    def __init__(self):
        super().__init__("TinyCI")
        
        self.add_url_rule("/tinyci/", view_func=self.__hello, methods=["GET"])
        self.add_url_rule("/tinyci/webhook", view_func=self.__webhook, methods=["POST"])
        self.__work_queue = queue.Queue()
        self.__latest_sha = {}
        
        threading.Thread(target=self.__worker, daemon=True).start()

    def __hello(self):
        return flask.Response("HELLO")

    def __webhook(self):
        event = flask.request.headers.get("X-GitHub-Event")

        if config.hook_secret is not None:
            hash_type, hash_value = flask.request.headers.get("X-Hub-Signature").split("=", 1)
            if hash_type != "sha1":
                log.info("Wrong hash type")
                flask.abort(400, "Invalid signature")
            if not hmac.compare_digest(hmac.new(config.hook_secret.encode('utf-8'), flask.request.get_data(), hashlib.sha1).hexdigest(), hash_value):
                log.info("Invalid signature")
                flask.abort(400, "Invalid signature")

        payload = json.loads(flask.request.form["payload"])
        if not "commits" in payload:
            return flask.Response("No commits")

        repos = payload["repository"]["full_name"]
        for commit in payload["commits"]:
            sha = commit["id"]
            github.updateStatus(repos, sha, "pending")
            self.__latest_sha[repos] = sha
            self.__addWork(repos, sha)
        return flask.Response("OK")

    def __addWork(self, repos, sha):
        self.__work_queue.put((repos, sha))
        for other_repos, data in config.repos.items():
            if repos in data.get("dep", []):
                self.__work_queue.put((other_repos, self.__getLatestSha(other_repos)))
    
    def __worker(self):
        for repos in config.repos.keys():
            has_hook = False
            for hook in github.getHooks(repos):
                if hook["config"]["url"] == config.hook_url:
                    has_hook = True
            if not has_hook:
                #github.addHook(repos, config.hook_url)
                self.__work_queue.put((repos, self.__getLatestSha(repos)))

        while True:
            repos, sha = self.__work_queue.get()
            log.info("Doing work for %s:%s", repos, sha)

            try:
                source_path = os.path.join(config.build_root, repos)
                git.checkout(repos, sha, source_path)

                build.make(source_path)

                github.updateStatus(repos, sha, "success")
            except Exception as e:
                log.exception("Exception %s while doing work", e)
                github.updateStatus(repos, sha, "failure")
                github.addComment(repos, sha, "### TinyCI build failure:\n%s" % (e))
            log.info("Finished work for %s:%s", repos, sha)

    def __getLatestSha(self, repos):
        if repos in self.__latest_sha:
            return self.__latest_sha[repos]
        self.__latest_sha[repos] = github.getLatestSha(repos)
        return self.__latest_sha[repos]

    def run(self):
        if stat.S_ISSOCK(os.fstat(0).st_mode):
            from flipflop import WSGIServer
            WSGIServer(self).run()
        else:
            super().run("0.0.0.0", 32032, threaded=True)


if __name__ == "__main__":
    logging.basicConfig(format="%(levelname)-8s %(name)-15s %(message)s", level=logging.INFO)
    TinyCIServer().run()
