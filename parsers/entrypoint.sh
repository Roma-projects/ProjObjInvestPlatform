#!/bin/sh
# Volume permissions are prepared by the Compose volume-permissions init service.
set -eu

storage_dir="${PARSERS_STORAGE_DIR:-/parsers_storage}"
mkdir -p "$storage_dir"
exec "$@"
