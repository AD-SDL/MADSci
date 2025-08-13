FROM python:3.12
LABEL org.opencontainers.image.source=https://github.com/AD-SDL/MADSci/
LABEL org.opencontainers.image.description="The Modular Autonomous Discovery for Science (MADSci) toolkit's base docker image."
LABEL org.opencontainers.image.licenses=MIT

# * Arguments and Environment Variables
ARG USER_ID=9999
ARG GROUP_ID=9999
ARG CONTAINER_USER=madsci
ENV PDM_CHECK_UPDATE=false

# * Install system dependencies
RUN apt-get update && \
	apt-get install -y gosu npm && \
	rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*
RUN npm install -g yarn
RUN --mount=type=cache,target=/root/.cache \
    pip install -U pdm

# * User Configuration
RUN groupadd -g ${GROUP_ID} ${CONTAINER_USER} && \
	useradd --create-home -u ${USER_ID} --shell /bin/bash -g ${CONTAINER_USER} ${CONTAINER_USER} && \
	mkdir -p /home/${CONTAINER_USER}/.madsci /home/${CONTAINER_USER}/MADSci && \
	chown -R ${USER_ID}:${GROUP_ID} /home/${CONTAINER_USER}/.madsci /home/${CONTAINER_USER}/MADSci

# * Install madsci entrypoint script
COPY madsci-entrypoint.sh /madsci-entrypoint.sh
RUN chmod +x /madsci-entrypoint.sh
ENTRYPOINT ["/madsci-entrypoint.sh"]

# * Install Python package and dependencies
WORKDIR /home/${CONTAINER_USER}
COPY pyproject.toml pdm.lock README.md /home/${CONTAINER_USER}/MADSci/
COPY src/ /home/${CONTAINER_USER}/MADSci/src
WORKDIR /home/${CONTAINER_USER}/MADSci
RUN --mount=type=cache,target=/root/.cache \
    pdm install -G:all -g -p . --check

WORKDIR /home/${CONTAINER_USER}
