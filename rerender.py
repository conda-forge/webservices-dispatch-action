import os
import json
import logging
import pprint
import tempfile
import subprocess

import urllib3.util.retry

from github import Github
from git import Repo, GitCommandError

LOGGER = logging.getLogger(__name__)


def create_api_sessions(github_token):
    """Create API sessions for GitHub.

    Parameters
    ----------
    github_token : str
        The GitHub access token.

    Returns
    -------
    gh : github.MainClass.Github
        A `Github` object from the PyGithub package.
    """
    gh = Github(
        github_token,
        retry=urllib3.util.retry.Retry(total=10, backoff_factor=0.1))

    return gh


def rerender(git_repo):
    LOGGER.info('rerendering')
    curr_head = git_repo.active_branch.commit
    ret = subprocess.call(
        ["conda", "smithy", "rerender", "-c", "auto"],
        cwd=git_repo.working_dir,
    )

    if ret:
        return False, True
    else:
        return git_repo.active_branch.commit != curr_head, False


def comment_and_push_per_changed(
    *,
    changed, rerender_error, git_repo, pull, pr_branch, pr_owner, pr_repo
):
    LOGGER.info(
        'pushing and commenting: branch|owner|repo = %s|%s|%s',
        pr_branch,
        pr_owner,
        pr_repo,
    )

    message = None
    if changed:
        try:
            git_repo.remotes.origin.push()
        except GitCommandError as e:
            LOGGER.critical(repr(e))
            message = """\
Hi! This is the friendly automated conda-forge-webservice.
I tried to rerender for you, but it looks like I wasn't able to push to the {}
branch of {}/{}. Did you check the "Allow edits from maintainers" box?
""".format(pr_branch, pr_owner, pr_repo)
    else:
        if rerender_error:
            doc_url = (
                "https://conda-forge.org/docs/maintainer/updating_pkgs.html"
                "#rerendering-with-conda-smithy-locally"
            )
            message = """\
Hi! This is the friendly automated conda-forge-webservice.
I tried to rerender for you but ran into some issues, please ping conda-forge/core
for further assistance. You can also try [re-rendering locally]({}).
""".format(doc_url)
        else:
            message = """\
Hi! This is the friendly automated conda-forge-webservice.
I tried to rerender for you, but it looks like there was nothing to do.
"""

    if message is not None:
        pull.create_issue_comment(message)


def main():
    logging.basicConfig(level=logging.INFO)

    LOGGER.info('making API clients')

    gh = create_api_sessions(os.environ["INPUT_GITHUB_TOKEN"])

    with open(os.environ["GITHUB_EVENT_PATH"], 'r') as fp:
        event_data = json.load(fp)
    event_name = os.environ['GITHUB_EVENT_NAME'].lower()

    LOGGER.info('github event: %s', event_name)
    LOGGER.info('github event data:\n%s', pprint.pformat(event_data))

    if event_name in ['repository_dispatch'] and event_data['action'] == 'rerender':
        pr_num = int(event_data['client_payload']['pr'])
        repo_name = event_data['repository']['full_name']

        gh_repo = gh.get_repo(repo_name)
        pr = gh_repo.get_pull(pr_num)

        with tempfile.TemporaryDirectory() as tmpdir:
            # clone the head repo
            pr_branch = pr.head.ref
            pr_owner = pr.head.repo.owner.login
            pr_repo = pr.head.repo.name
            repo_url = "https://%s:%s@github.com/%s/%s.git" % (
                os.environ['GITHUB_ACTOR'],
                os.environ['INPUT_GITHUB_TOKEN'],
                pr_owner,
                pr_repo,
            )
            feedstock_dir = os.path.join(
                tmpdir,
                pr_repo,
            )
            git_repo = Repo.clone_from(
                repo_url,
                feedstock_dir,
                branch=pr_branch,
            )

            # rerender
            changed, rerender_error = rerender(git_repo)

            # comment
            comment_and_push_per_changed(
                changed=changed,
                rerender_error=rerender_error,
                git_repo=git_repo,
                pull=pr,
                pr_branch=pr_branch,
                pr_owner=pr_owner,
                pr_repo=pr_repo,
            )
    else:
        raise ValueError('GitHub event %s cannot be processed!' % event_name)


if __name__ == '__main__':
    main()
