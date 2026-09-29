#!/bin/bash
set -e
EP=${AWS_ENDPOINT_URL:-http://floci:4566}
aws --endpoint-url $EP ecr create-repository --repository-name lomax-backend || true
aws --endpoint-url $EP ecr create-repository --repository-name lomax-frontend || true
URI_B=$(aws --endpoint-url $EP ecr describe-repositories --repository-names lomax-backend --query 'repositories[0].repositoryUri' --output text)
URI_F=$(aws --endpoint-url $EP ecr describe-repositories --repository-names lomax-frontend --query 'repositories[0].repositoryUri' --output text)
echo "URIs: $URI_B $URI_F"
TAG=$(git rev-parse --short HEAD 2>/dev/null || echo latest)
docker build -t $URI_B:$TAG ./backend; docker push $URI_B:$TAG
docker build -t $URI_F:$TAG ./frontend; docker push $URI_F:$TAG
aws --endpoint-url $EP ecr describe-images --repository-name lomax-backend
docker rmi $URI_B:$TAG || true
docker pull $URI_B:$TAG
docker images --digests | grep lomax || true
