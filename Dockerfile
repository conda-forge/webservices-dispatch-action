FROM frolvlad/alpine-glibc:alpine-3.10

# much of image code ripped from
# https://github.com/Docker-Hub-frolvlad/docker-alpine-miniconda3
COPY BASE_IMAGE_LICENSE /

LABEL maintainer="conda-forge (@conda-forge/core)"

ENV LANG en_US.UTF-8

ARG CONDA_MD5="678c0078e3a37596cd671f690e852fff"
ARG CONDA_DIR="/opt/conda"

ENV PATH="$CONDA_DIR/bin:$PATH"
ENV PYTHONDONTWRITEBYTECODE=1

# make sure the install below is not cached by docker
ADD http://worldclockapi.com/api/json/utc/now /opt/docker/etc/timestamp

# Install conda
RUN echo "**** install dev packages ****" && \
    apk add --no-cache bash ca-certificates wget && \
    \
    echo "**** get Miniconda ****" && \
    mkdir -p "$CONDA_DIR" && \
    wget "https://github.com/conda-forge/miniforge/releases/download/4.11.0-0/Mambaforge-4.11.0-0-Linux-x86_64.sh" -O miniconda.sh && \
    echo "$CONDA_MD5  miniconda.sh" | md5sum -c && \
    \
    echo "**** install Miniconda ****" && \
    bash miniconda.sh -f -b -p "$CONDA_DIR" && \
    \
    echo "**** install base env ****" && \
    source /opt/conda/etc/profile.d/conda.sh && \
    conda activate base && \
    conda config --set show_channel_urls True  && \
    conda config --add channels conda-forge  && \
    conda config --show-sources  && \
    conda config --set always_yes yes && \
    conda config --set channel_priority strict && \
    mamba update --all && \
    mamba install --quiet \
        git \
        python=3.8 \
        conda-smithy \
        conda-forge-pinning \
        conda-build \
        pip \
        tini \
        pygithub \
        requests \
        gitpython \
        pyyaml && \
    \
    echo "**** cleanup ****" && \
    rm -rf /var/cache/apk/* && \
    rm -f miniconda.sh && \
    conda clean --all --force-pkgs-dirs --yes && \
    find "$CONDA_DIR" -follow -type f \( -iname '*.a' -o -iname '*.pyc' -o -iname '*.js.map' \) -delete && \
    \
    echo "**** finalize ****" && \
    mkdir -p "$CONDA_DIR/locks" && \
    chmod 777 "$CONDA_DIR/locks"

COPY entrypoint /opt/docker/bin/entrypoint
RUN mkdir -p webservices_dispatch_action
COPY / webservices_dispatch_action/
RUN cd webservices_dispatch_action && \
    source /opt/conda/etc/profile.d/conda.sh && \
    conda activate base && \
    pip install -e .

ENTRYPOINT ["/opt/conda/bin/tini", "--", "/opt/docker/bin/entrypoint"]
CMD ["/bin/bash"]
