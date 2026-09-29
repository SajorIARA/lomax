# Diagrama Lomax (desplegado = diagrama)

```mermaid
flowchart LR
  U[Usuario :8080] --> P[proxy nginx]
  P --> F[frontend nginx :80]
  P --> B[backend Flask :3000]
  B --> R[(RDS Postgres Floci :7001)]
  B --> D[(DynamoDB Floci :4566)]
  B --> S3[(S3 originales/miniaturas :4566)]
  B --> L[Lambda thumbnail]
  L --> S3
  BIMG[lomax-backend:latest] --> ECR[ECR Floci]
  FIMG[lomax-frontend:latest] --> ECR
  ECR --> K3S[EKS k3s :6500]
  K3S --> B
```

- Red `lomax_net`, volumen `floci-data`. Solo proxy publica al host (:8080); Floci :4566 publicado solo por el data-plane ECR que usa el daemon.
- EKS k3s real vía Floci (endpoint `https://localhost:6500`). Pods resuelven `floci` por `hostAliases` a `192.168.96.2` (documentado en `infra/eks/deploy.yaml`) porque k3s no ve los alias de Compose.
- Auth EKS con usuario IAM `eks-admin` (el par `test/test` lo rechaza el webhook a propósito).
- ECR con `URI_STYLE=path` porque el daemon solo acepta HTTP en `localhost` literal.
