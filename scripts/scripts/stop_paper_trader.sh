#!/bin/bash
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
exec "$ROOT/start.sh" stop
