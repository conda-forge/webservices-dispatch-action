import os
import logging
import pprint
import subprocess

from git import GitCommandError
from conda.models.version import VersionOrder

from conda_forge_tick.utils import setup_logger
from conda_forge_tick.feedstock_parser import load_feedstock
from conda_forge_tick.update_upstream_versions import get_latest_version

from conda_forge_tick.update_sources import (
    PyPI,
    CRAN,
    NPM,
    ROSDistro,
    RawURL,
    Github,
    IncrementAlphaRawURL,
    NVIDIA,
)
import conda_forge_tick.update_recipe

from .api_sessions import get_actor_token

setup_logger(logging.getLogger("conda_forge_tick"))
LOGGER = logging.getLogger(__name__)


def update_version(git_repo, repo_name, input_version=None):
    name = os.path.basename(repo_name).rsplit("-", 1)[0]
    LOGGER.info("using feedstock name %s for repo %s", name, repo_name)

    try:
        LOGGER.info("computing feedstock attributes")
        attrs = load_feedstock(name, {})
        LOGGER.info("feedstock attrs:\n%s\n", pprint.pformat(attrs))
    except Exception:
        LOGGER.exception("error while computing feedstock attributes!")
        return False, True

    if input_version is None or input_version == "null":
        try:
            LOGGER.info("getting latest version")
            new_version = get_latest_version(
                name,
                attrs,
                (
                    PyPI(),
                    CRAN(),
                    NPM(),
                    ROSDistro(),
                    RawURL(),
                    Github(),
                    IncrementAlphaRawURL(),
                    NVIDIA(),
                ),
            )
            new_version = new_version["new_version"]
            if new_version:
                LOGGER.info(
                    "curr version|latest version: %s|%s",
                    attrs.get("version", "0.0.0"),
                    new_version,
                )
            else:
                raise RuntimeError("Could not fetch latest version!")
        except Exception:
            LOGGER.exception("error while getting feedstock version!")
            return False, True
    else:
        LOGGER.info("using input version")
        new_version = input_version
        LOGGER.info(
            "curr version|input version: %s|%s",
            attrs.get("version", "0.0.0"),
            new_version,
        )

    # if we are finding the version automatically, check that it is going up
    if (
        (input_version is None or input_version == "null")
        and (
            VersionOrder(str(new_version).replace("-", "."))
            <= VersionOrder(str(attrs.get("version", "0.0.0")).replace("-", "."))
        )
    ):
        LOGGER.info(
            "not updating since new version is less or equal to current version"
        )
        return False, False

    try:
        new_meta_yaml, errors = conda_forge_tick.update_recipe.update_version(
            attrs["raw_meta_yaml"],
            str(new_version),
        )
        if errors or new_meta_yaml is None:
            LOGGER.critical("errors when updating the recipe: %r", errors)
            raise RuntimeError("Error updating the recipe!")
        new_meta_yaml = conda_forge_tick.update_recipe.update_build_number(
            new_meta_yaml,
            0,
        )
    except Exception:
        LOGGER.exception("error while updating the recipe!")
        return False, True

    try:
        with open(os.path.join(git_repo.working_dir, "recipe", "meta.yaml"), "w") as fp:
            fp.write(new_meta_yaml)

        subprocess.run(
            "git add recipe/meta.yaml",
            shell=True,
            cwd=git_repo.working_dir,
            check=True,
        )

        subprocess.run(
            f"git commit -m 'ENH updated version to {new_version}'",
            shell=True,
            cwd=git_repo.working_dir,
            check=True,
        )
    except Exception:
        LOGGER.exception("error while committing new recipe to repo")
        return False, True

    return True, False


def _get_run_link(repo_name):
    run_id = os.environ["GITHUB_RUN_ID"]
    return f"https://github.com/{repo_name}/actions/runs/{run_id}"


def version_comment_and_push_per_changed(
    *,
    changed, version_error, git_repo, pull, pr_branch, pr_owner, pr_repo,
    repo_name,
):
    actor, token, can_change_workflows = get_actor_token()
    LOGGER.info(
        'token can change workflows: %s', can_change_workflows,
    )

    LOGGER.info(
        'pushing and commenting: branch|owner|repo = %s|%s|%s',
        pr_branch,
        pr_owner,
        pr_repo,
    )

    run_link = _get_run_link(repo_name)

    push_error = False
    message = None
    if changed:
        try:
            git_repo.remotes.origin.set_url(
                "https://%s:%s@github.com/%s/%s.git" % (
                    actor,
                    token,
                    pr_owner,
                    pr_repo,
                ),
                push=True,
            )
            git_repo.remotes.origin.push()
        except GitCommandError as e:
            push_error = True
            LOGGER.critical(repr(e))
            message = """\
Hi! This is the friendly automated conda-forge-webservice.

I tried to update the version for you, but it looks like I wasn't \
able to push to the {} \
branch of {}/{}. Did you check the "Allow edits from maintainers" box?

**NOTE**: PRs from organization accounts or PRs from forks made from \
organization forks cannot be rerendered because of GitHub \
permissions. Please fork the feedstock directly from conda-forge \
into your personal GitHub account.
""".format(pr_branch, pr_owner, pr_repo)
        finally:
            git_repo.remotes.origin.set_url(
                "https://github.com/%s/%s.git" % (
                    pr_owner,
                    pr_repo,
                ),
                push=True,
            )
    else:
        if version_error:
            message = """\
Hi! This is the friendly automated conda-forge-webservice.

I tried to update the version for you but ran into some issues. \
Please check the output \
logs of the latest webservices GitHub actions workflow run for errors. You can \
also ping conda-forge/core for further assistance.
"""
        else:
            message = """\
Hi! This is the friendly automated conda-forge-webservice.

I tried to update the version for you, but it looks like there was nothing to do.

I am closing this PR!
"""

    if message is not None:
        if run_link is not None:
            message += (
                "\nThis message was generated by "
                f"GitHub actions workflow run [{run_link}]({run_link}).\n"
            )

        pull.create_issue_comment(message)

    if not changed and not version_error:
        pull.edit(state="closed")

    return push_error
