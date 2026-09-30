# Lomax SA — Catálogo con flujo PENDIENTE → PUBLICADO sobre AWS local (Floci)

Tienda de equipos (teclados, pantallas, audio) donde el catálogo **solo muestra productos PUBLICADOS**.
Un producto nace **PENDIENTE** en RDS y se publica únicamente cuando tiene **atributos en DynamoDB**
y **miniatura generada por Lambda**. Todo corre local en contenedores contra **Floci**
(`floci/floci:latest`), emulador AWS de puerto único 4566.

## Arquitectura

```
Usuario :8080 → proxy (nginx) → frontend (nginx :80) + backend (Flask :3000)
                                        ↓
Floci :4566 → S3 (originales/miniaturas) · DynamoDB (atributos) · Lambda (thumbnail)
            → RDS Postgres real (proxy :7001) · ECR (registry:2) · EKS (k3s :650x)
```

- Una red interna `lomax_net`; solo el proxy publica puerto al host (`8080:80`).
- Volumen `floci-data:/app/data`: los datos sobreviven reinicios.
- En el host solo se necesita Docker, Git y el editor; AWS CLI, `psql` y scripts corren en el contenedor `tools`.

## Inicio rápido

```bash
cp .env.example .env
docker compose up -d --build
docker compose exec tools bash
# dentro de tools (AWS_ENDPOINT_URL=http://floci:4566):
bash infra/s3/crear-buckets.sh
./scripts/e2-rds.sh        # crea instancia RDS + aplica infra/rds/model.sql
./scripts/e3-s3-lambda.sh  # despliega la Lambda thumbnail
./scripts/carga-20.sh      # 20 productos con foto (7/7/6)
```

- Catálogo: http://localhost:8080/ · Registro: http://localhost:8080/nuevo.html · API: http://localhost:8080/api/

## Flujo de negocio

`PENDIENTE` (RDS) → atributos (DynamoDB, mismo `producto_id`) → original (S3) →
Lambda genera `thumbs/{id}.jpg` (clave determinista, máx. 300×300 proporcional:
1200×800 → 300×200) → **PUBLICADO** solo con atributos + miniatura.
Imagen inválida o fallo → sigue PENDIENTE con imagen `ERROR`.

## API y códigos

| Endpoint | Éxito | Errores |
|---|---|---|
| `GET /api/categorias` | 200 | — |
| `POST /api/productos` | 201 | 400 (validación) · 409 (código duplicado) · 502/503 (Dynamo caído, conserva PENDIENTE) |
| `POST /api/productos/{id}/imagen` | 200/201 | 400/404/413 (>5 MB)/415 (no JPEG/PNG) |
| `POST /api/productos/{id}/reprocesar` | 200 | 404 · 409 (sin original) |
| `GET /api/productos` (solo PUBLICADOS) | 200 | — |
| `GET /api/productos/{id}` | 200 | 404 |
| `GET /api/productos/{id}/imagen` | 200 | 404 |

## Estructura

```
backend/ frontend/ proxy/ tools/      imágenes propias + contenedor de utilidades
infra/{floci,rds,dynamodb,s3,lambda,ecr,eks}/   IaC y manifiestos
datos/{imagenes,productos}/           20 fotos + dataset idempotente
scripts/                              pruebas por etapa (e1..e7, carga-20)
docs/{documento-tecnico.md,arquitectura/,conceptos/,evidencias/}  entregables
tablero/                              roles y tareas por etapa
```

## Documentos

- `docs/documento-tecnico.md` — Entregable 2 (herramientas, imágenes, red, persistencia, Compose, ECR).
- `docs/arquitectura/diagrama.md` — diagrama + decisiones verificadas en docs de Floci.
- `docs/conceptos/tablas.md` — tabla Saber-Conocer por etapa.
- `docs/evidencias/E{1..7}-*/` — salidas SQL, Dynamo, Lambda, endpoints, digests, UIDs.

## Equipo y reparto

- Backend + DevOps (Compose, Floci, ECR, EKS) · Persistencia + S3/Lambda · Frontend + diagrama/docs.
- Defensa: cada integrante explica el flujo completo. Tablero en `tablero/tablero.md`.
