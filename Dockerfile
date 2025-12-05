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
	apt-get install -y gosu npm wget && \
	rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*

# * Install MongoDB tools from official binaries (works for all architectures)
RUN ARCH=$(dpkg --print-architecture) && \
	echo "Detected architecture: $ARCH" && \
	if [ "$ARCH" = "amd64" ]; then MONGO_ARCH="x86_64"; elif [ "$ARCH" = "arm64" ]; then MONGO_ARCH="arm64"; else echo "Unsupported architecture: $ARCH" && exit 1; fi && \
	echo "Using MongoDB architecture: $MONGO_ARCH" && \
	wget -v "https://fastdl.mongodb.org/tools/db/mongodb-database-tools-ubuntu2204-${MONGO_ARCH}-100.13.0.tgz" -O /tmp/mongodb-tools.tgz && \
	echo "Download completed, extracting..." && \
	tar -xzf /tmp/mongodb-tools.tgz -C /tmp && \
	echo "Installing tools to /usr/local/bin/" && \
	cp /tmp/mongodb-database-tools-*/bin/* /usr/local/bin/ && \
	chmod +x /usr/local/bin/mongo* && \
	echo "Cleaning up..." && \
	rm -rf /tmp/mongodb-* && \
	echo "MongoDB tools installed successfully" && \
	ls -la /usr/local/bin/mongo*

# * Install PostgreSQL client tools
RUN apt-get update && \
	apt-get install -y postgresql-client && \
	rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/* && \
	echo "PostgreSQL client tools installed successfully" && \
	pg_dump --version
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
 	pdm install -G:all -g -p . --no-lock

# * Fix ownership of all MADSci files and ensure alembic directories exist with correct permissions
RUN chown -R ${USER_ID}:${GROUP_ID} /home/${CONTAINER_USER}/MADSci && \
	mkdir -p /home/${CONTAINER_USER}/MADSci/src/madsci_resource_manager/madsci/resource_manager/alembic/versions && \
	chown -R ${USER_ID}:${GROUP_ID} /home/${CONTAINER_USER}/MADSci/src/madsci_resource_manager/madsci/resource_manager/alembic/versions
WORKDIR /home/${CONTAINER_USER}
