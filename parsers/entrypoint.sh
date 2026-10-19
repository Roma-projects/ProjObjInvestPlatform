#!/bin/sh
# Перед запуском приложения отдаёт отдельный том Parsers непривилегированному пользователю.
set -eu

storage_dir="${PARSERS_STORAGE_DIR:-/parsers_storage}"
mkdir -p "$storage_dir"
chown -R parsers:parsers "$storage_dir"
exec gosu parsers "$@"
