import time
import os
import requests
import urllib3.util.retry

from github import Github


def get_actor_token():
    # we use the token reset time as a proxy for when it expires
    # by default the app tokens have 1 hour and that is the same as the token
    # reset time.
    # I could not figure out how to get the actual reset time.
    now = time.time()
    reset_time = now - 10  # default the token to "expired"
    if (
        "INPUT_RERENDERING_GITHUB_TOKEN" in os.environ
        and len(os.environ["INPUT_RERENDERING_GITHUB_TOKEN"]) > 0
    ):
        try:
            # make sure the token works
            gh = Github(os.environ["INPUT_RERENDERING_GITHUB_TOKEN"])
            reset_time = gh.rate_limiting_resettime
        except Exception:
            gh = None
    else:
        gh = None

    if gh is not None and reset_time > now:
        return "x-access-token", os.environ["INPUT_RERENDERING_GITHUB_TOKEN"], True
    else:
        return "x-access-token", os.environ["INPUT_GITHUB_TOKEN"], False


def create_api_sessions(github_token):
    """Create API sessions for GitHub.

    Parameters
    ----------
    github_token : str
        The GitHub access token.

    Returns
    -------
    session : requests.Session
        A `requests` session w/ the beta `check_run` API configured.
    gh : github.MainClass.Github
        A `Github` object from the PyGithub package.
    """
    # based on
    #  https://alexwlchan.net/2019/03/
    #    creating-a-github-action-to-auto-merge-pull-requests/
    # with lots of edits
    sess = requests.Session()
    sess.headers = {
        "Accept": "; ".join([
            "application/vnd.github.v3+json",
            # special beta api for check_suites endpoint
            "application/vnd.github.antiope-preview+json",
        ]),
        "Authorization": f"token {github_token}",
        "User-Agent": f"GitHub Actions script in {__file__}"
    }

    def raise_for_status(resp, *args, **kwargs):
        try:
            resp.raise_for_status()
        except Exception as e:
            print('ERROR:', resp.text)
            raise e

    sess.hooks["response"].append(raise_for_status)

    # build a github object too
    gh = Github(
        github_token,
        retry=urllib3.util.retry.Retry(total=10, backoff_factor=0.1))

    return sess, gh
