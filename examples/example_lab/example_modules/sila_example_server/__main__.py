"""Entry point for the MADSci SiLA2 example server."""

import argparse
import contextlib
import logging
import signal

from .server import Server

logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="MADSci SiLA2 Example Server")
    parser.add_argument(
        "-a",
        "--ip-address",
        default="0.0.0.0",  # noqa: S104
        help="The IP address to bind to",
    )
    parser.add_argument(
        "-p", "--port", type=int, default=50052, help="The port to listen on"
    )
    parser.add_argument(
        "--insecure", action="store_true", help="Start without encryption"
    )
    parser.add_argument(
        "--disable-discovery", action="store_true", help="Disable SiLA Server Discovery"
    )
    parser.add_argument("--server-name", default=None, help="Override server name")
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose logging"
    )
    args = parser.parse_args()

    # Logging setup
    level = logging.INFO if args.verbose else logging.WARNING
    logging.basicConfig(
        level=level, format="%(asctime)s:%(levelname)s:%(name)s:%(message)s"
    )
    logger.setLevel(logging.INFO)

    # Create and start server
    server = Server(name=args.server_name)

    try:
        if args.insecure:
            server.start_insecure(
                args.ip_address, args.port, enable_discovery=not args.disable_discovery
            )
        else:
            server.start(
                args.ip_address, args.port, enable_discovery=not args.disable_discovery
            )
    except Exception:
        logger.exception("Server startup failed, shutting down")
        if server.running:
            server.stop()
        return

    logger.info(
        "SiLA example server started on %s:%d (insecure=%s)",
        args.ip_address,
        args.port,
        args.insecure,
    )
    signal.signal(signal.SIGTERM, lambda *_args: server.grpc_server.stop(grace=5))

    with contextlib.suppress(KeyboardInterrupt):
        server.grpc_server.wait_for_termination()

    server.stop()
    logger.info("Server shutdown complete")


if __name__ == "__main__":
    main()
