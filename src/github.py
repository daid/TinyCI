import config
import requests
import json
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

def _request(type, url, **kwargs):
    global _token
    if _token is None:
        _getToken()
    headers = {"Authorization": "Token %s" % (_token), "Accept": "application/vnd.github.machine-man-preview+json"}
    if "headers" in kwargs:
        headers.update(kwargs.pop("headers"))
    result = requests.request(type, "https://api.github.com/%s" % (url), **kwargs, headers=headers)
    if result.status_code == 401:
        _token = None
        return _request(type, url, **kwargs)
    return result

def getAllRepositories():
    result = []
    for repo in _request("GET", "installation/repositories").json()["repositories"]:
        result.append(repo["full_name"])
    return result

def getFileContents(repos, sha, filename):
    res = requests.get("https://raw.githubusercontent.com/%s/%s/%s" % (repos, sha, filename))
    if res.status_code == 404:
        return ""
    return res.text

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
