import flask
import stat
import os
import logging
import json
import requests
import threading
import queue
import configparser
import subprocess

import config
import git
import github
import hmac
import hashlib
import build
import repositoryInfo
import run

log = logging.getLogger(__name__.split(".")[-1])


class TinyCIServer(flask.Flask):
    def __init__(self):
        super().__init__("TinyCI")

        self.add_url_rule("/tinyci/", view_func=self.__home, methods=["GET"])
        self.add_url_rule("/tinyci/webhook", view_func=self.__webhook, methods=["POST"])
        self.__work_queue = queue.Queue()
        self.__repositories = {}

        threading.Thread(target=self.__worker, daemon=True).start()

    def __home(self):
        result = """<html><head>
            <script>document.addEventListener("visibilitychange", function(event) { if (!document.hidden) location.reload(); }, false);</script>
            <style>
            .infobox { width: 200px; border: solid; text-align: center; float: left }
            .status_unknown { background-color: #A0A0A0 }
            .status_success { background-color: #40FF40 }
            .status_failure { background-color: #FF4040 }
            .status_pending { background-color: #FFFF40 }
            </style></head><body>"""
        for repos in sorted(self.__repositories):
            info = self.__repositories[repos]
            if info.has_config:
                result += "<div class='infobox status_%s'>%s</div>" % (info.status, repos)
        result += "<br/><br/><br/><br/><br/>"
        result += "%s jobs waiting" % (self.__work_queue.qsize())
        result += "<hr/><pre>"
        result += "".join(run.getRunningData())
        result += "</pre></body></html>"
        return flask.Response(result)

    def __webhook(self):
        event = flask.request.headers.get("X-GitHub-Event")

        if config.hook_secret is not None:
            hash_type, hash_value = flask.request.headers.get("X-Hub-Signature").split("=", 1)
            if hash_type != "sha1":
                flask.abort(400, "Invalid signature")
            if not hmac.compare_digest(hmac.new(config.hook_secret.encode('utf-8'), flask.request.get_data(), hashlib.sha1).hexdigest(), hash_value):
                flask.abort(400, "Invalid signature")

        event_type = flask.request.headers.get("X-GitHub-Event")

        payload = flask.request.json
        log.info("Webhook: %s: %s", event_type, payload)

        if event_type == "push":
            if not "commits" in payload:
                return flask.Response("No commits")
            repos = payload["repository"]["full_name"]
            for commit in payload["commits"]:
                sha = commit["id"]
                for r in self.__repositories.values():
                    r.onNewCommit(repos, sha)
        elif event_type == "create":
            repos = payload["repository"]["full_name"]
            tag_name = payload["ref"]
            if payload["ref_type"] == "tag":
                self.__repositories[repos].onNewTag(tag_name)
        return flask.Response("OK")

    def __worker(self):
        for repos in github.getAllRepositories():
            self.__repositories[repos] = repositoryInfo.RepositoryInfo(repos, self.__work_queue)

        log.info("Work queue started")
        while True:
            build_function, sha = self.__work_queue.get()
            try:
                build_function(sha)
            except:
                log.exception("Exception in build_function")

    def run(self):
        if stat.S_ISSOCK(os.fstat(0).st_mode):
            from flipflop import WSGIServer
            WSGIServer(self).run()
        else:
            super().run("0.0.0.0", 32032, threaded=True)


if __name__ == "__main__":
    logging.basicConfig(format="%(levelname)-8s %(name)-15s %(message)s", level=logging.INFO)
    TinyCIServer().run()
