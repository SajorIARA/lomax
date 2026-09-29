#!/bin/bash
set -e
EP=${AWS_ENDPOINT_URL:-http://floci:4566}
aws --endpoint-url $EP s3 mb s3://lomax-originales || true
aws --endpoint-url $EP s3 mb s3://lomax-miniaturas || true
aws --endpoint-url $EP s3 ls
