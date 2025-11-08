#!/bin/bash
#set -e
set -o pipefail

DEFAULT_CONTAINER_USER=madsci

# *Change the UID and GID of the CONTAINER_USER user if they are provided as environment variables
if [ -z "${USER_ID}" ]; then
    USER_ID=9999
fi
if [ -z "${GROUP_ID}" ]; then
    GROUP_ID=9999
fi
if [ -z ${CONTAINER_USER} ]; then
    CONTAINER_USER=${DEFAULT_CONTAINER_USER}
fi
if [ "$USER_ID" -eq 0 ] && [ "$GROUP_ID" -eq 0 ]; then
    echo "Running as root"
else
    echo "Running as ${CONTAINER_USER} with UID ${USER_ID} and GID ${GROUP_ID}"
fi

if [ "$USER_ID" -ne 0 ] && [ "$USER_ID" -ne 9999 ]; then
    GROUP_LIST=$(groups ${DEFAULT_CONTAINER_USER})
    userdel ${DEFAULT_CONTAINER_USER}
elif [ "$GROUP_ID" -ne 0 ] && [ "$GROUP_ID" -ne 9999 ]; then
    groupdel ${DEFAULT_CONTAINER_USER}
fi
if [ "$GROUP_ID" -ne 0 ] && [ "$GROUP_ID" -ne 9999 ] && ! getent group $GROUP_ID > /dev/null; then
    groupadd -g $GROUP_ID ${CONTAINER_USER}
fi
if [ "$USER_ID" -ne 0 ] && [ "$USER_ID" -ne 9999 ]; then
    useradd -u $USER_ID --shell /bin/bash -g ${GROUP_ID} ${CONTAINER_USER}
    usermod -aG $(echo "$GROUP_LIST" | sed 's/.*: //; s/ /,/g') ${CONTAINER_USER}
fi

# *Best-effort attempt to align permissions for the default data directory
mkdir -p /home/${CONTAINER_USER}/.madsci
mkdir -p /home/${CONTAINER_USER}/.madsci/logs
chown $USER_ID:$GROUP_ID /home/${CONTAINER_USER} || true
chown $USER_ID:$GROUP_ID /home/${CONTAINER_USER}/.madsci || true
chown $USER_ID:$GROUP_ID /home/${CONTAINER_USER}/.madsci/logs || true
# Prepare writable dirs used at runtime (no recursive chown)
# Backups
install -d -m 0775 -o "${USER_ID}" -g "${GROUP_ID}" /home/${CONTAINER_USER}/.madsci/mongodb/backups || true
install -d -m 0775 -o "${USER_ID}" -g "${GROUP_ID}" /home/${CONTAINER_USER}/.madsci/postgres/backups || true

# Alembic revisions (repo location) — make ONLY this dir writable
ALEMBIC_VERSIONS_DIR="${ALEMBIC_VERSIONS_DIR:-/home/${CONTAINER_USER}/MADSci/src/madsci_resource_manager/madsci/resource_manager/alembic/versions}"
install -d -m 0775 -o "${USER_ID}" -g "${GROUP_ID}" "${ALEMBIC_VERSIONS_DIR}" || true
chown "${USER_ID}:${GROUP_ID}" "${ALEMBIC_VERSIONS_DIR}" || true


# *Run the container command as the specified user
if [ "$USER_ID" -eq 0 ] && [ "$GROUP_ID" -eq 0 ]; then
    # *If we are root, easiest thing to do is to symlink everything from /home/${CONAINER_USER} to /root
    shopt -s dotglob
    for item in /home/${CONTAINER_USER}/*; do
        dest="/root/$(basename "$item")"

        if [ ! -e "$dest" ]; then
            ln -s "$item" "$dest"
        fi
    done
    shopt -u dotglob
    exec "$@"
else
    # *If we are not root, we need to drop privileges
    exec gosu ${CONTAINER_USER} "$@"
fi
