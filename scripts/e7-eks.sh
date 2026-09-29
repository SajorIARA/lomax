#!/bin/bash
set -e
EP=${AWS_ENDPOINT_URL:-http://floci:4566}
aws --endpoint-url $EP eks create-cluster --name lomax --role-arn arn:aws:iam::000000000000:role/eks --resources-vpc-config subnetIds=subnet-1 || true
aws --endpoint-url $EP eks describe-cluster --name lomax || true
kubectl get nodes || echo "configurar kubeconfig con puerto k3s 6500-6599 (ver docs EKS Floci)"
kubectl apply -f infra/eks/deploy.yaml
kubectl scale deploy lomax-backend --replicas=3
kubectl get pods -o wide
echo "UID antes/después: kubectl get pods -o jsonpath='{.items[*].metadata.uid}'"
