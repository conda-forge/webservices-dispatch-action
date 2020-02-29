# webservices-dispatch-action
a GitHub action to rerender conda-forge feedstocks

You can build a dev docker image via

```bash
docker build -t condaforge/webservices-dispatch-action:dev .
docker push condaforge/webservices-dispatch-action:dev
```

Then point your repo at the dev branch in the GitHub Actions workflow file 
to use the dev image.
