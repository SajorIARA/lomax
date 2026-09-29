# Lomax SA — Guía esencial (tu parte: backend + DevOps)

## Arquitectura
`proxy (:8080) -> frontend, backend (:3000) -> Floci (:4566) -> S3/DynamoDB/Lambda/RDS/ECR/EKS`
Solo proxy publica puerto al host. Red `lomax_net`. Volumen `floci-data:/app/data` para no perder datos.

Floci real (floci/floci:latest):
- Puerto único 4566 para todas las API AWS.
- RDS: contenedor Postgres real + proxy TCP 7001-7099. Requiere `/var/run/docker.sock`.
- ECR: sidecar `registry:2`, puertos 5100-5199 con bind directo en host, sin mapping en compose.
- EKS: contenedores k3s, API 6500-6599 con bind directo, var `FLOCI_SERVICES_EKS_DOCKER_NETWORK`.
- Lambda: contenedores `public.ecr.aws/lambda/*`.
- Docs verificadas: floci.io/floci/services/{rds,ecr,s3,lambda,eks} + configuration/{ports,storage,docker}.

Si EKS no diera Kubernetes real, se levanta k3s ligero (k3s-in-docker) y se documenta. Floci sí trae k3s real, así que se usa tal cual.

## Uso rápido
```bash
cp .env.example .env
docker compose up -d --build
docker compose exec tools bash
# dentro de tools:
./scripts/e1-base.sh
./scripts/e2-rds.sh
./scripts/e3-s3-lambda.sh
./scripts/e4-backend.sh
```
Frontend: http://localhost:8080 — API: http://localhost:8080/api/

## Flujo negocio
PENDIENTE (RDS) -> atributos (DynamoDB, mismo producto_id) -> original (S3) -> Lambda thumb 300x300 prop. (1200x800->300x200) -> PUBLICADO solo si atributos+miniatura. Si imagen inválida/fallo -> PENDIENTE + imagen ERROR. Clave thumb determinista: `thumbs/{id}.jpg`.

## Endpoints
GET /api/categorias, POST /api/productos, POST /api/productos/{id}/imagen, POST /api/productos/{id}/reprocesar, GET /api/productos, GET /api/productos/{id}, GET /api/productos/{id}/imagen
