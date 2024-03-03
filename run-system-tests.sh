#!/bin/sh
set -e

docker compose -f docker-compose-system-tests.yml build
docker compose -f docker-compose-system-tests.yml up --no-log-prefix --remove-orphans --force-recreate --abort-on-container-exit --exit-code-from system-tests
