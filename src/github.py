import config
import requests
import json


def updateStatus(repos, sha, status):
    requests.post(
        "https://api.github.com/repos/%s/statuses/%s" % (repos, sha),
        data=json.dumps({"state": status, "context": "TinyCI"}),
        auth=(config.github_user, config.github_token)
    )

def addComment(repos, sha, comment):
    reply = requests.post(
        "https://api.github.com/repos/%s/commits/%s/comments" % (repos, sha),
        data=json.dumps({"body": comment}),
        auth=(config.github_user, config.github_token)
    )

def getLatestSha(repos):
    branch = requests.get(
        "https://api.github.com/repos/%s" % (repos),
        auth=(config.github_user, config.github_token)
    ).json()["default_branch"]
    reply = requests.get(
        "https://api.github.com/repos/%s/commits/%s" % (repos, branch),
        headers={"accept": "application/vnd.github.VERSION.sha"},
        auth=(config.github_user, config.github_token)
    )
    return reply.text

def getHooks(repos):
    return requests.get(
        "https://api.github.com/repos/%s/hooks" % (repos),
        auth=(config.github_user, config.github_token)
    ).json()

def addHook(repos, url):
    reply = requests.post(
        "https://api.github.com/repos/%s/hooks" % (repos),
        data=json.dumps({"name": "web", "config": {"url": url, "secret": config.hook_secret}}),
        auth=(config.github_user, config.github_token)
    )
