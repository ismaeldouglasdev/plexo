#!/bin/bash
# Serve plexo API + UI
# Usage: ./serve.sh [port] [--mock]
exec python3 "$(dirname "$0")/server.py" "$@"
