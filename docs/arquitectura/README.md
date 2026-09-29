# Arquitectura Lomax (contrastar con despliegue)
[proxy:8080] -> [frontend:80] [backend:3000] -> [floci:4566 S3/Dynamo/Lambda/ECR/EKS] -> [RDS proxy 7001 Postgres real] 
Red lomax_net, volumen floci-data. Diagrama con íconos AWS en docs/arquitectura/diagrama.png (pendiente integrante 3).
Verificación Floci: RDS real Docker, ECR registry:2, EKS k3s real (FLOCI_SERVICES_EKS_DOCKER_NETWORK). Si k3s no bastara, k3d ligero documentado.
