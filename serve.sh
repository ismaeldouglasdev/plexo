#!/bin/bash
# Serve plexo API + UI
PORT=${1:-8080}
exec python3 "$(dirname "$0")/server.py" "$PORT"
