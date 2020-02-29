# rerender-action

a GitHub action to rerender conda-forge feedstocks

## Usage

To use this action, add the following YAML file at `.github/workflows/rerender.yml`

```yaml
on: repository_dispatch

jobs:
  rerender-action:
    runs-on: ubuntu-latest
    name: rerender-action
    steps:
      - name: rerender-action
        id: rerender-action
        uses: conda-forge/rerender-action@master
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
```

The admin web service will create the appropriate `dispatch` event with the
correct data

```json
{"event_type": "rerender", "client_payload": {"pr": 12}}
```

## Deployment

The GitHub action always points to the `prod` tag of the
[condaforge/rerender-action](https://hub.docker.com/repository/docker/condaforge/rerender-action)
Docker image.

 - To redeploy the rerender action, push a new image to the `prod` tag.

   ```bash
   docker build -t condaforge/rerender-action:dev .
   docker push condaforge/rerender-action:prod
   ```

 - To take the rerender action down, delete the tag from the Docker repository.
   The GitHub Action will still run in this case, but it will always fail.
