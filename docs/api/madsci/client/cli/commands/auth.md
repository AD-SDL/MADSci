Module madsci.client.cli.commands.auth
======================================
MADSci CLI ``auth`` command group.

Subcommands target the Auth Manager via ``AuthClient``. The bootstrap
command runs locally against an Auth Manager instance (operator must already
have access to the database / process); all other commands talk to a running
Auth Manager over HTTP.