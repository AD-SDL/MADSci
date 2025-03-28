FROM python:3.12
LABEL org.opencontainers.image.source=https://github.com/AD-SDL/MADSci/
LABEL org.opencontainers.image.description="The Modular Autonomous Discovery for Science (MADSci) toolkit's base docker image."
LABEL org.opencontainers.image.licenses=MIT

RUN set -eux; \
	apt update; \
	apt install -y gosu; \
	rm -rf /var/lib/apt/lists/*

# User configuration
ARG USER_ID=9999
ARG GROUP_ID=9999
ARG CONTAINER_USER=madsci

RUN groupadd -g ${GROUP_ID} ${CONTAINER_USER}
RUN useradd --create-home -u ${USER_ID} --shell /bin/bash -g ${CONTAINER_USER} ${CONTAINER_USER}

WORKDIR /home/${CONTAINER_USER}

# Create working directories
RUN mkdir -p /home/${CONTAINER_USER}/.madsci
RUN mkdir -p /home/${CONTAINER_USER}/MADSci

# install PDM
RUN pip install -U pdm
# disable update check
ENV PDM_CHECK_UPDATE=false
# use uv
# RUN pdm config use_uv true
# copy files
COPY pyproject.toml pdm.lock README.md /home/${CONTAINER_USER}/MADSci/
COPY src/ /home/${CONTAINER_USER}/MADSci/src

WORKDIR /home/${CONTAINER_USER}/MADSci
RUN --mount=type=cache,target=/root/.cache \
    pdm install -G:all -g -p . --check

COPY madsci-entrypoint.sh /madsci-entrypoint.sh
RUN chmod +x /madsci-entrypoint.sh
ENTRYPOINT ["/madsci-entrypoint.sh"]
WORKDIR /home/${CONTAINER_USER}
