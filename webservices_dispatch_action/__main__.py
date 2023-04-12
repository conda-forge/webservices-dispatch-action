import os
import json
import logging
import pprint
import tempfile

from git import Repo

from webservices_dispatch_action.api_sessions import (
    create_api_sessions, get_actor_token
)
from webservices_dispatch_action.rerendering import (
    rerender,
    rerender_comment_and_push_per_changed,
)
from webservices_dispatch_action.version_updater import (
    update_version,
    version_comment_and_push_per_changed
)


LOGGER = logging.getLogger(__name__)


def main():
    logging.basicConfig(level=logging.INFO)

    LOGGER.info('making API clients')

    _, gh = create_api_sessions(os.environ["INPUT_GITHUB_TOKEN"])

    with open(os.environ["GITHUB_EVENT_PATH"], 'r') as fp:
        event_data = json.load(fp)
    event_name = os.environ['GITHUB_EVENT_NAME'].lower()

    LOGGER.info('github event: %s', event_name)
    LOGGER.info('github event data:\n%s\n', pprint.pformat(event_data))

    if event_name in ['repository_dispatch']:
        if event_data['action'] == 'rerender':
            pr_num = int(event_data['client_payload']['pr'])
            repo_name = event_data['repository']['full_name']

            gh_repo = gh.get_repo(repo_name)
            pr = gh_repo.get_pull(pr_num)

            if pr.state == 'closed':
                raise ValueError("Closed PRs cannot be rerendered!")

            with tempfile.TemporaryDirectory() as tmpdir:
                # clone the head repo
                pr_branch = pr.head.ref
                pr_owner = pr.head.repo.owner.login
                pr_repo = pr.head.repo.name
                repo_url = "https://github.com/%s/%s.git" % (
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
                _, _, can_change_workflows = get_actor_token()
                changed, rerender_error = rerender(git_repo, can_change_workflows)

                # comment
                push_error = rerender_comment_and_push_per_changed(
                    changed=changed,
                    rerender_error=rerender_error,
                    git_repo=git_repo,
                    pull=pr,
                    pr_branch=pr_branch,
                    pr_owner=pr_owner,
                    pr_repo=pr_repo,
                    repo_name=repo_name,
                )

                if rerender_error or push_error:
                    raise RuntimeError(
                        "Rerendering failed! error in push|rerender: %s|%s" % (
                            push_error,
                            rerender_error,
                        ),
                    )
        elif event_data['action'] == 'version_update':
            pr_num = int(event_data['client_payload']['pr'])
            repo_name = event_data['repository']['full_name']

            gh_repo = gh.get_repo(repo_name)
            pr = gh_repo.get_pull(pr_num)

            if pr.state == 'closed':
                raise ValueError("Closed PRs cannot be rerendered!")

            with tempfile.TemporaryDirectory() as tmpdir:
                # clone the head repo
                pr_branch = pr.head.ref
                pr_owner = pr.head.repo.owner.login
                pr_repo = pr.head.repo.name
                repo_url = "https://github.com/%s/%s.git" % (
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

                _, _, can_change_workflows = get_actor_token()

                # update version
                version_changed, version_error = update_version(git_repo, repo_name)
                version_push_error = version_comment_and_push_per_changed(
                    changed=changed,
                    version_error=version_error,
                    git_repo=git_repo,
                    pull=pr,
                    pr_branch=pr_branch,
                    pr_owner=pr_owner,
                    pr_repo=pr_repo,
                    repo_name=repo_name,
                )

                if version_error or version_push_error:
                    raise RuntimeError(
                        "Updating version failed! error in "
                        "push|version update: %s|%s" % (
                            version_push_error,
                            version_error,
                        ),
                    )

                if version_changed:
                    # rerender
                    rerender_changed, rerender_error = rerender(
                        git_repo, can_change_workflows
                    )
                    rerender_push_error = rerender_comment_and_push_per_changed(
                        changed=changed,
                        rerender_error=rerender_error,
                        git_repo=git_repo,
                        pull=pr,
                        pr_branch=pr_branch,
                        pr_owner=pr_owner,
                        pr_repo=pr_repo,
                        repo_name=repo_name,
                    )

                    if rerender_error or rerender_push_error:
                        raise RuntimeError(
                            "Rerendering failed! error in push|rerender: %s|%s" % (
                                push_error,
                                rerender_error,
                            ),
                        )
        else:
            raise ValueError(
                'Dispatch action %s cannot be processed!' % event_data['action'])
    else:
        raise ValueError('GitHub event %s cannot be processed!' % event_name)
