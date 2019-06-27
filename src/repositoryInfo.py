import configparser
import logging
import os

import github
import config


class RepositoryInfo:
    def __init__(self, repos: str, work_queue) -> None:
        self.__repos = repos
        self.__work_queue = work_queue
        self.__latest_commit_sha = github.getLatestSha(repos)
        self.__getConfig()

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

    def onNewCommit(self, repos: str, new_sha: str) -> None:
        if repos == self.__repos:
            logging.info("Got commit on %s:%s", self.__repos, new_sha)
            config = self.__getConfig(new_sha)
            if config is not None:
                logging.info("[MAIN] Adding work for %s:%s", repos, sha)
                github.updateStatus(repos, sha, "pending")
                self.__work_queue.put((self.build, sha))
            self.__latest_commit_sha = sha

        if self.__last_config is not None and self.__last_config.getboolean("repos-%s" % (repos), "required", fallback=False):
            logging.info("[DEP] Adding work for %s", self.__repos)
            github.updateStatus(self.__repos, self.__latest_commit_sha, "pending")
            self.__work_queue.put((self.build, self.__latest_commit_sha))

    def build(self, sha):
        logging.info("Doing work for %s:%s", repos, sha)
        try:
            source_path = os.path.join(config.build_root, self.__repos)
            git.checkout(self.__repos, sha, source_path)

            build.make(source_path)

            github.updateStatus(self.__repos, sha, "success")
        except Exception as e:
            logging.exception("Exception %s while doing work", e)
            github.updateStatus(self.__repos, sha, "failure")
            github.addComment(self.__repos, sha, "### TinyCI build failure:\n%s" % (e))
        logging.info("Finished work for %s:%s", repos, sha)
