#!/usr/bin/env bash
# Non-interactive: read config from the environment.
: "${DB_PASSWORD:?set DB_PASSWORD}"
echo "configured"
