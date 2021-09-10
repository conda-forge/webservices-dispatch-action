"""
This script will run a live integration test of the rerendering
action. To use it do the following

1. Make sure you have a valid github token in your environment called
   "GH_TOKEN".
2. Make surre you have pushed the new version of the action to the `dev`
   docker image tag.

   You can run

      docker build -t condaforge/webservices-dispatch-action:dev .
      docker push condaforge/webservices-dispatch-action:dev

   or pass `--build-and-push` when running the test script.

Then you can execute this script and it will report the results.

## setup

 - The script uses a PR on the `conda-forge/cf-autotick-bot-test-package-feedstock`.
 - The head ref for this PR is on a fork of that feedstock in the regro
   organization.
 - It works by pushing a change to the PR branch that would cause a rerender
   to happen.
 - Then we trigger the rerender and check that it happened.

"""
import os
import json
import time
import tempfile
import requests
import contextlib
import subprocess
import argparse


@contextlib.contextmanager
def pushd(new_dir):
    previous_dir = os.getcwd()
    os.chdir(new_dir)
    try:
        yield
    finally:
        os.chdir(previous_dir)


def _run_test():
    print('sending repo dispatch event to rerender...')
    headers = {
        "authorization": "Bearer %s" % os.environ['GH_TOKEN'],
        'content-type': 'application/json',
    }
    r = requests.post(
        ("https://api.github.com/repos/conda-forge/"
         "cf-autotick-bot-test-package-feedstock/dispatches"),
        data=json.dumps({"event_type": "rerender", "client_payload": {"pr": 19}}),
        headers=headers,
    )
    print('    dispatch event status code:', r.status_code)
    assert r.status_code == 204

    print('sleeping for a few minutes to let the rerender happen...')
    tot = 0
    while tot < 180:
        time.sleep(10)
        tot += 10
        print("    slept %s seconds out of 180" % tot, flush=True)

    print('checking repo for the rerender...')
    with tempfile.TemporaryDirectory() as tmpdir:
        with pushd(tmpdir):
            print("cloning...")
            os.system(
                "git clone "
                "https://github.com/conda-forge/"
                "cf-autotick-bot-test-package-feedstock.git",
            )

            with pushd("cf-autotick-bot-test-package-feedstock"):
                print("checkout branch...")
                os.system("git checkout rerender-live-test")

                print("checking the git history")
                c = subprocess.run(
                    ["git", "log", "--pretty=oneline", "-n", "1"],
                    capture_output=True,
                )
                output = c.stdout.decode('utf-8')
                print("    last commit:", output.strip())
                assert "MNT:" in output

    print('tests passed!')


def _change_action_branch(branch):
    print("moving repo to %s action" % branch, flush=True)
    os.system("git checkout master")

    with open(".github/workflows/webservices.yml", "w") as fp:
        fp.write("""\
on: repository_dispatch

jobs:
  webservices:
    runs-on: ubuntu-latest
    name: webservices
    steps:
      - name: webservices
        id: webservices
        uses: conda-forge/webservices-dispatch-action@%s
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
""" % branch)

    print("commiting...", flush=True)
    os.system("git add .github/workflows/webservices.yml")
    os.system(
        "git commit "
        "-m "
        "'[ci skip] move rerender action to branch %s'" % branch
    )

    print("push to origin...", flush=True)
    os.system("git push")


parser = argparse.ArgumentParser(
    description="Run a live test of the rerendering code",
)
parser.add_argument(
    "--build-and-push",
    help="build and push the docker image to the dev tag before running the tests",
    action="store_true",
)
args = parser.parse_args()

if args.build_and_push:
    subprocess.run(
        "docker build -t condaforge/webservices-dispatch-action:dev .",
        shell=True,
    )
    subprocess.run(
        "docker push condaforge/webservices-dispatch-action:dev",
        shell=True,
    )


print('making an edit to the head ref...')
with tempfile.TemporaryDirectory() as tmpdir:
    with pushd(tmpdir):
        print("cloning...")
        os.system(
            "git clone "
            "https://github.com/conda-forge/"
            "cf-autotick-bot-test-package-feedstock.git",
        )

        with pushd("cf-autotick-bot-test-package-feedstock"):
            try:
                _change_action_branch("dev")

                print("checkout branch...")
                os.system("git checkout rerender-live-test")

                print("removing files...")
                os.system("git rm .ci_support/*.yaml")

                print("git status...")
                os.system("git status")

                print("commiting...")
                os.system(
                    "git commit "
                    "-m "
                    "'remove ci scripts to trigger rerender'"
                )

                print("push to origin...")
                os.system("git push")

                _run_test()

            finally:
                _change_action_branch("master")
