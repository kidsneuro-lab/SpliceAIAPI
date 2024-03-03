#!/bin/sh
set -e

docker compose -f docker-compose-system-test.yml build
docker compose -f docker-compose-system-test.yml up --no-log-prefix --remove-orphans --force-recreate --abort-on-container-exit --exit-code-from spliceai_api
