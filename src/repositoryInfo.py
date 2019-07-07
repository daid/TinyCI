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

    def onNewTag(self, tag: str) -> None:
        config = self.__getConfig(tag)
        if config is not None:
            self.triggerRelease(tag)

    def triggerBuild(self, origin: str) -> None:
        logging.info("[%s] Adding work for %s", origin, self.__repos)
        self.__setStatus("pending", self.__latest_commit_sha)
        self.__work_queue.put((self.build, self.__latest_commit_sha))

    def triggerRelease(self, tag: str) -> None:
        logging.info("[RELEASE] Adding work to release %s as %s", self.__repos, tag)
        self.__work_queue.put((self.release, tag))

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

    def release(self, tag):
        logging.info("Doing to release %s:%s", self.__repos, tag)
        try:
            source_path = os.path.join(config.build_root, self.__repos)
            git.checkout(self.__repos, tag, source_path)
            build.make(source_path)
            config_file = configparser.ConfigParser()
            config_file.read(os.path.join(source_path, ".tinycy"))
            release_id = github.addRelease(self.__repos, tag)
            for section_name, section in filter(lambda n: n[0].startswith("build-") or n[0] == "build", config_file.items()):
                for artifact in section.get("artifacts", "").strip().split("\n"):
                    if os.path.isfile(os.path.join(source_path, artifact)):
                        github.addReleaseAsset(self.__repos, release_id, os.path.join(source_path, artifact))
            github.publishRelease(self.__repos, release_id)
        except Exception as e:
            logging.exception("Exception %s while trying to release", e)
        logging.info("Finished release for %s:%s", self.__repos, tag)

    @property
    def status(self):
        return self.__status

    @property
    def has_config(self):
        return self.__last_config is not None
