FROM ghcr.io/prefix-dev/pixi:0.26.1 AS build
USER root

# make sure the install below is not cached by docker
COPY . /app

RUN pixi run install

# Create the shell-hook bash script to activate the environment
RUN pixi shell-hook -e default > /shell-hook.sh

FROM ubuntu:22.04 AS production

# only copy the production environment into prod container
# please note that the "prefix" (path) needs to stay the same as in the build container
COPY --from=build /app/.pixi/envs/default /app/.pixi/envs/default
COPY --from=build /shell-hook.sh /shell-hook.sh

WORKDIR /app
EXPOSE 8000

LABEL maintainer="conda-forge (@conda-forge/core)"

ENV LANG en_US.UTF-8

COPY entrypoint /opt/docker/bin/entrypoint
RUN mkdir -p webservices_dispatch_action

ENTRYPOINT ["/opt/conda/bin/tini", "--", "/opt/docker/bin/entrypoint"]

