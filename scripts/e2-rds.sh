#!/bin/bash
set -e
EP=${AWS_ENDPOINT_URL:-http://floci:4566}
echo "== E2 RDS =="
aws --endpoint-url $EP rds create-db-instance --db-instance-identifier lomax-postgres --db-instance-class db.t3.micro --engine postgres --master-username lomax --master-user-password lomax123 --allocated-storage 20 || true
aws --endpoint-url $EP rds describe-db-instances --query 'DBInstances[*].[DBInstanceIdentifier,Endpoint.Address,Endpoint.Port,DBInstanceStatus]' --output table || true
echo "--- aplicar model.sql (psql al puerto proxy descubierto) ---"
PORT=$(aws --endpoint-url $EP rds describe-db-instances --query 'DBInstances[0].Endpoint.Port' --output text 2>/dev/null || echo 7001)
HOST=$(aws --endpoint-url $EP rds describe-db-instances --query 'DBInstances[0].Endpoint.Address' --output text 2>/dev/null || echo floci)
echo "endpoint $HOST:$PORT"
PGPASSWORD=lomax123 psql -h ${HOST:-floci} -p ${PORT:-7001} -U lomax -d postgres -f infra/rds/model.sql || echo "psql pendiente: revisar puerto"
echo "--- 4 casos: usar backend ---"
echo "válido/duplicado/precio negativo/categoría inexistente -> ver scripts/e4-backend.sh"
