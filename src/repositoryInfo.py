import configparser
import logging
import os

import github
import git
import build
import config


class RepositoryInfo:
    def __init__(self, repos: str, work_queue) -> None:
        self.__repos = repos
        self.__work_queue = work_queue
        self.__latest_commit_sha = github.getLatestSha(repos)
        self.__status = "unknown"
        if self.__getConfig() is not None:
            self.triggerBuild("INIT")

    def __getConfig(self, sha=None):
        sha = sha or self.__latest_commit_sha
        logging.info("Getting tinyci config for: %s:%s", self.__repos, sha)
        config_file = github.getFileContents(self.__repos, sha, ".tinyci")
        config = None
        if config_file != "":
            config = configparser.ConfigParser()
            config.read_string(config_file)
        self.__last_config = config
        return config

    def __setStatus(self, status: str, sha: str) -> None:
        github.updateStatus(self.__repos, sha, "success")
        if self.__latest_commit_sha == sha:
            self.__status = status

    def onNewCommit(self, repos: str, new_sha: str) -> None:
        if repos == self.__repos:
            logging.info("Got commit on %s:%s", self.__repos, new_sha)
            self.__latest_commit_sha = new_sha
            config = self.__getConfig(new_sha)
            if config is not None:
                self.triggerBuild("MAIN")

        if self.__last_config is not None and self.__last_config.getboolean("repos-%s" % (repos), "required", fallback=False):
            self.triggerBuild("DEB")

    def triggerBuild(self, origin: str) -> None:
        logging.info("[%s] Adding work for %s", origin, self.__repos)
        self.__setStatus("pending", self.__latest_commit_sha)
        self.__work_queue.put((self.build, self.__latest_commit_sha))

    def build(self, sha):
        logging.info("Doing work for %s:%s", self.__repos, sha)
        try:
            source_path = os.path.join(config.build_root, self.__repos)
            git.checkout(self.__repos, sha, source_path)
            build.make(source_path)
            self.__setStatus("success", sha)
        except Exception as e:
            logging.exception("Exception %s while doing work", e)
            self.__setStatus("failure", sha)
            github.addComment(self.__repos, sha, "### TinyCI build failure:\n%s" % (e))
        logging.info("Finished work for %s:%s", self.__repos, sha)

    @property
    def status(self):
        return self.__status

    @property
    def has_config(self):
        return self.__last_config is not None
