"""
This script will run a live integration test of the rerendering
action. To use it do the following

1. Make sure you have a valid github token in your environment called
   "GITHUB_TOKEN".
2. Make surre you have pushed the new version of the action to the `dev`
   docker image tag. See the README.md on the `dev` branch of this repo
   for more details.

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

import requests


print('making an edit to the head ref...')


print('sending repo dispatch event to rerender...')
headers = {
    "authorization": "Bearer %s" % os.environ['GITHUB_TOKEN'],
    'content-type': 'application/json',
}
r = requests.post(
    ("https://api.github.com/repos/conda-forge/"
     "cf-autotick-bot-test-package-feedstock/dispatches"),
    data=json.dumps({"event_type": "rerender", "client_payload": {"pr": 18}}),
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
