# Entregable 2 — Documento técnico: construcción de la solución Lomax SA

## A. Preparación (herramientas y versiones verificadas el 30/09/2026)

| Herramienta | Versión | Rol |
|---|---|---|
| Docker | 29.8.1 | Único runtime instalado en el host; construye imágenes y corre contenedores |
| Docker Compose | 5.5.1 (plugin) | Orquesta los 5 servicios del proyecto |
| Git | 2.55.0 | Versionado (`lomax/.git`, 11+ commits) |
| Floci `floci/floci:latest` | 2.1.0 (nativo Quarkus) | Emulador AWS: S3, DynamoDB, Lambda, ECR, EKS, RDS en un contenedor, puerto único 4566 |
| AWS CLI (en contenedor `tools`) | v2 vía `awscli` pip | Crea buckets, tablas, funciones, repos, clúster |
| `psql` (en `tools`) | postgresql-client Debian | Aplica `infra/rds/model.sql` y evidencias SQL |
| Python 3.12-slim | base de `backend` y `tools` | Flask 3.1, boto3 1.34, Pillow 10.4, psycopg2 2.9 |
| nginx:alpine | `frontend` y `proxy` | Estáticos y reverse proxy |
| PostgreSQL | `postgres:16-alpine` (imagen RDS por defecto de Floci) | Motor real del servicio RDS |
| Lambda runtime | `public.ecr.aws/lambda/python:3.12` | Contenedor real de la función thumbnail |
| ECR backing | `registry:2` | Registry OCI real detrás del API ECR |
| EKS | k3s (nodo `v1.34.1+k3s1`) | Kubernetes real por clúster Floci |
| kubectl | `bitnami/kubectl:latest` (contenedor efímero) | Opera el clúster sin instalar nada en el host |

Regla del entorno: en el host solo existen Docker, Git y el editor. AWS CLI, Node/Python, scripts y pruebas corren en el contenedor `tools`.

## B. Construcción de las imágenes propias

### B.1 Backend (`backend/`: `app.py`, `requirements.txt`, `Dockerfile`)
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
ENV BACKEND_PORT=3000
EXPOSE 3000
CMD ["python","app.py"]
```
- `FROM python:3.12-slim`: base mínima con Python (coincide con el runtime Lambda 3.12).
- `COPY requirements.txt` + `pip install --no-cache-dir`: instala Flask, boto3, psycopg2, Pillow en una capa cacheable (si solo cambia `app.py`, no reinstala).
- `EXPOSE 3000` documenta el puerto; `CMD` arranca Flask en `0.0.0.0:3000`.
- Construcción: `docker compose build backend` (imagen `lomax-backend:latest`, ~269 MB).

### B.2 Frontend (`frontend/`: `index.html`, `producto.html`, `nuevo.html`, `Dockerfile`)
```dockerfile
FROM nginx:alpine
COPY index.html producto.html nuevo.html /usr/share/nginx/html/
EXPOSE 80
```
- Sirve las 3 vistas como estáticos (catálogo, detalle, registro). Sin build JS: cero dependencias.
- Construcción: `docker compose build frontend` (`lomax-frontend:latest`, ~95 MB).

### B.3 Proxy (`proxy/`: `nginx.conf`, `Dockerfile`)
```dockerfile
FROM nginx:alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```
`nginx.conf`: `location /api/` → `http://backend:3000`, `location /` → `http://frontend:80`.
- Construcción: `docker compose build proxy` (`lomax-proxy:latest`).

### B.4 Tools (`tools/Dockerfile`)
```dockerfile
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends curl jq git postgresql-client unzip && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir boto3 psycopg2-binary pillow requests flask awscli
WORKDIR /trabajo
CMD ["sleep","infinity"]
```
- Lleva AWS CLI, `psql`, `curl`/`jq` y las mismas libs Python del backend. Monta `./:/trabajo` y el socket Docker.
- Construcción: `docker compose build tools` (`lomax-tools:latest`).

## C. Networking

- **Red creada**: `lomax_lomax_net` (driver `bridge`, creada por Compose). Es la única red del proyecto.
- **Servicios conectados**: `floci`, `backend`, `frontend`, `proxy`, `tools` + contenedores hijos de Floci (RDS Postgres, Lambda, registry ECR, k3s EKS) gracias a `FLOCI_SERVICES_DOCKER_NETWORK: lomax_lomax_net`.
- **Justificación**: una sola red interna minimiza superficie y DNS: los servicios se resuelven por nombre (`backend`, `floci`, `proxy`). Solo el proxy publica puerto al host (`8080:80`); el resto usa `expose`. Excepción documentada: Floci publica `4566:4566` porque el **daemon Docker del host** hace `push/pull` al data-plane ECR sobre ese listener (el proxy sigue siendo la única entrada de la aplicación). Los pods k3s resuelven `floci` por `hostAliases` (`infra/eks/deploy.yaml`), pues k3s no ve los alias de Compose.

## D. Persistencia

| Volumen (Docker) | Servicio | Datos dentro del contenedor | Prueba realizada |
|---|---|---|---|
| `lomax_floci-data` → `/app/data` | `floci` | Metadatos Floci (tablas Dynamo, buckets S3, funciones Lambda, registros RDS/EKS) con `FLOCI_STORAGE_MODE=persistent` | `docker restart lomax-floci` → catálogo sigue en 20; clúster EKS se re-ata a su contenedor |
| `floci-rds-db-*` (gestionado por Floci) | RDS `lomax-postgres` | Archivos de PostgreSQL 16 | `DELETE` + recreación de pods y reinicio: `SELECT` devuelve los 20 productos |
| `floci-eks-lomax` | EKS `lomax` | etcd/datos k3s | Tras borrar+recrear el clúster, `kubectl get pods` devuelve los deployments (volumen retenido) |
| `floci-ecr-registry-data` | ECR (`registry:2`) | Capas/blob de imágenes | `docker rmi` + `docker pull` recupera el mismo digest |
| `floci-code-lomax-thumbnail-*` | Lambda | Código desempaquetado de la función | Re-invocaciones usan el mismo artefacto |

Prueba global de persistencia (ejecutada): con todo publicado (20/20/20) se reinició Floci y se borraron todos los pods del backend; el catálogo volvió a 20 sin recargar nada.

## E. Docker Compose (`docker-compose.yml` completo en la raíz)

Servicios: `floci` (imagen `floci/floci:latest`, socket Docker montado, `floci-data:/app/data`, env de storage/red/puertos RDS y `FLOCI_SERVICES_ECR_URI_STYLE=path`), `backend` y `tools` (con `env_file: .env`), `frontend`, `proxy` (único con `ports: 8080:80`). Red única `lomax_net`, volumen único `floci-data`. Arranque: `cp .env.example .env && docker compose up -d --build`.

Puertos: `8080→proxy/80` (host); `4566` Floci (API AWS + ECR, ver §C); `7001-7099` proxy RDS (uso interno/tools); `5100-5199` registry y `6500-6599` k3s con bind directo del daemon (sin mapping). Imágenes: 1 externa (`floci/floci:latest`) + 4 propias (`lomax-*`).

## F. Docker Hub / Floci ECR

Floci ECR emula Docker Hub en local (misma API y comandos `docker`). Repositorios: `lomax-backend`, `lomax-frontend` (URIs `localhost:4566/000000000000/us-east-1/<repo>` en estilo `path`, pues el daemon solo acepta HTTP en `localhost` literal).

```bash
# login (Floci acepta cualquier password con get-login-password)
aws --endpoint-url http://localhost:4566 ecr get-login-password | docker login --username AWS --password-stdin localhost:4566/000000000000/us-east-1/lomax-backend
# tag ligado al commit + latest para EKS
TAG=$(git rev-parse --short HEAD)   # ej. 37137b4
docker tag lomax-backend:latest localhost:4566/000000000000/us-east-1/lomax-backend:$TAG
docker tag lomax-backend:latest localhost:4566/000000000000/us-east-1/lomax-backend:latest
docker push localhost:4566/000000000000/us-east-1/lomax-backend:$TAG
docker push localhost:4566/000000000000/us-east-1/lomax-backend:latest
# (igual para lomax-frontend)
aws --endpoint-url http://floci:4566 ecr describe-images --repository-name lomax-backend
# pull en limpio y comparación de digests
docker rmi localhost:4566/000000000000/us-east-1/lomax-backend:$TAG
docker pull localhost:4566/000000000000/us-east-1/lomax-backend:$TAG
docker images --digests | grep lomax-backend   # push == pull: sha256:4bf19bb0…
```

Digests verificados: backend `sha256:4bf19bb0e014…`, frontend `sha256:9becdf2f2e52…` (ver `docs/evidencias/E6-ecr/digests.txt`). La imagen descargada se ejecutó contra el RDS real (`{"db":"pg"}` + catálogo) y es la que corren los pods EKS.
