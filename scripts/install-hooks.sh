#!/usr/bin/env sh
set -eu
ROOT="$(git rev-parse --show-toplevel)"
git config core.hooksPath .githooks
echo "Git hooks installed (core.hooksPath=.githooks)"
