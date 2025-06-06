# Example MADSci Lab

This is a fully functional example of a MADSci-powered self driving laboratory. It includes basic examples of each manager included in the MADSci core package, as well as three simple virtual nodes: a robot arm, liquidhandler, and platereader node.

## Starting the Example Lab

You can start the example lab using docker (compose) and the provided `compose.yaml` file in the root of this repository. This will launch all required services in containers, configured to work together. See the [Environment Setup](../README.md#environment-setup) section of the main README for information on installing docker.

### Starting the Example Lab

From the root of the repository, run:

```sh
docker compose up
```

Or, if you are using Podman:

```sh
podman-compose up
```

This will start all the services defined in the compose file. You can then access and interact with the example lab as described in the following sections.

### Configuring the Example Lab

- You can modify the configuration of the lab by making changes to the `.env`, modifying the compose services to set environment variables or pass command line arguments, creating `.env` or settings files for specific components, or using secrets files.
- For more details and to see what options are available for a specific MADSci component, see [Configuration.md](../Configuration.md) and [.env.example](../.env.example).
- For details on MADSci settings in general, see the `madsci.common` packages [README](../src/madsci_common/README.md#settings)
