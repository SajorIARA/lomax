# Conceptos P1 — Saber Conocer (resumen por etapa)
| Etapa | Concepto | Evidencia |
|---|---|---|
| E1 | Emulador Floci un puerto 4566, volumen persistente | docs/evidencias/E1-arquitectura/ |
| E2 | RDS Postgres real, UNIQUE, CHECK precio>=0, FK categoría, sin parciales | E2-persistencia/rds.txt |
| E2 | DynamoDB mismo producto_id, verificación sin FK entre servicios | E2-persistencia/dynamo.json |
| E3 | S3 dos buckets, Lambda Pillow 300x300 proporcional, clave determinista | E3-s3-lambda/ |
| E4 | API 200/201/400/404/409/413/415/502-503, idempotencia | E4-backend/ |
| E5 | Catálogo solo PUBLICADOS, 3 vistas, proxy | E5-frontend/catalogo.json |
| E6 | ECR push tag=commit, pull limpio, digests iguales | E6-ecr/ |
| E7 | EKS k3s 3 réplicas, UID antes/después, persistencia | E7-eks/uid-*.txt |
