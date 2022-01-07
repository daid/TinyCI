import config
import requests
import json
import base64
import os
import urllib.parse
from cryptography.hazmat.backends import default_backend
import jwt
import time


_token = None

def _getToken():
    private_key = default_backend().load_pem_private_key(open(config.github_keyfile, "rb").read(), None)
    payload = {
        'iat': int(time.time()),
        'exp': int(time.time() + (10 * 60)),
        'iss': config.github_app_id,
    }
    actual_jwt = jwt.encode(payload, private_key, algorithm='RS256')
    headers = {"Authorization": "Bearer {}".format(actual_jwt.decode()),
               "Accept": "application/vnd.github.machine-man-preview+json"}
    resp = requests.post('https://api.github.com/installations/%s/access_tokens' % (config.github_install_id),
                     headers=headers)
    global _token
    _token = resp.json()["token"]

def _request(type, url, *, hostname="api.github.com", **kwargs):
    global _token
    if _token is None:
        _getToken()
    headers = {"Authorization": "Token %s" % (_token), "Accept": "application/vnd.github.machine-man-preview+json"}
    if "headers" in kwargs:
        headers.update(kwargs.pop("headers"))
    result = requests.request(type, "https://%s/%s" % (hostname, url), timeout=60, **kwargs, headers=headers)
    if result.status_code == 401:
        _token = None
        return _request(type, url, **kwargs)
    return result

def getAllRepositories():
    result = []
    page_nr = 0
    while True:
        page_nr += 1
        repos = _request("GET", "installation/repositories?page=%d&per_page=100" % (page_nr)).json()["repositories"]
        if len(repos) == 0:
            return result
        for repo in repos:
            result.append(repo["full_name"])

def getFileContents(repos, sha, filename):
    res = _request("GET", "repos/%s/contents/%s?ref=%s" % (repos, filename, sha))
    if res.status_code == 404:
        return ""
    try:
        return base64.b64decode(res.json()["content"]).decode("utf-8")
    except:
        return ""

def updateStatus(repos, sha, status):
    res = _request("POST", "repos/%s/statuses/%s" % (repos, sha),
        data=json.dumps({"state": status, "context": "TinyCI"}),
    )

def addComment(repos, sha, comment):
    res = _request("POST", "repos/%s/commits/%s/comments" % (repos, sha),
        data=json.dumps({"body": comment})
    )

def getLatestSha(repos):
    branch = _request("GET", "repos/%s" % (repos)).json()["default_branch"]
    reply = _request("GET", "repos/%s/commits/%s" % (repos, branch),
        headers={"Accept": "application/vnd.github.VERSION.sha"},
    )
    return reply.text

def addRelease(repos, tag):
    reply = _request("POST", "repos/%s/releases" % (repos), data=json.dumps({"tag_name": tag, "draft": True}))
    return reply.json()["id"]

def addReleaseAsset(repos, release_id, filename, *, name=None):
    if name is None:
        name = os.path.basename(filename)
    res = _request("POST", "repos/%s/releases/%s/assets?%s" % (repos, release_id, urllib.parse.urlencode({"name": name})),
        hostname="uploads.github.com",
        data=open(filename, "rb").read(),
        headers={"Content-Type": "application/octet-stream"})
    return res

def publishRelease(repos, release_id, prerelease=False):
    res = _request("PATCH", "repos/%s/releases/%s" % (repos, release_id), data=json.dumps({"draft": False, "prerelease": prerelease}))
    return res
