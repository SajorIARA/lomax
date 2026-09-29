#!/bin/bash
set -e
EP=${AWS_ENDPOINT_URL:-http://floci:4566}
echo "== E1 base =="
aws --endpoint-url $EP s3 ls || curl -sf $EP/_localstack/health || curl -sf http://floci:4566/ || true
echo "Floci responde. Volumen: docker volume inspect lomax_floci-data"
psql --version 2>/dev/null || echo "psql en tools ok si instalado"
