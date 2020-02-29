import requests
import os
import json


headers = {
    "authorization": "Bearer %s" % os.environ['GITHUB_TOKEN'],
    'content-type': 'application/json',
}
r = requests.post(
    ("https://api.github.com/repos/conda-forge/"
     "cf-autotick-bot-test-package-feedstock/dispatches"),
    data=json.dumps({"event_type": "rerender", "client_payload": {"pr": 12}}),
    headers=headers,
)
print(r.status_code)
