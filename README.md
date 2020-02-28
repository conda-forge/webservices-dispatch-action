# rerender-action

a GitHub action to rerender conda-forge feedstocks

## Usage

To use this action, add the following YAML file at `.github/workflows/rerender.yml`

```yaml
on:
  pull_request:
    types:
      - labeled

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

## Deployment

The GitHub action always points to the `prod` tag of the
[condaforge/rerender-action](https://hub.docker.com/repository/docker/condaforge/rerender-action)
Docker image.

 - To redeploy the bot, push a new image to the `prod` tag.
 - To take the bot down, delete the tag from the Docker repository. The GitHub Action
   will still run in this case, but it will always fail.
