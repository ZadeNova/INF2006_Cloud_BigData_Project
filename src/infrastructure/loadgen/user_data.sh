#!/bin/bash
# Tools the load harness needs (tests/load/README.md): Python 3.12 to run Locust, git and tmux so a long run survives
# a dropped session. chronyc (time sync, for the clock-offset check) is already part of Amazon Linux 2023.
set -euxo pipefail
dnf install -y python3.12 python3.12-pip git tmux
touch /var/lib/loadgen-ready
