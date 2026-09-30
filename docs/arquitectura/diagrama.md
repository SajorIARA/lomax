# Diagrama Lomax (desplegado = diagrama)

```mermaid
flowchart TB
    subgraph Client["CAPA CLIENTE"]
        User(["<img src='https://cdn-icons-png.flaticon.com/512/847/847969.png' width='45'/><br/><b>Usuario</b><br/>navegador :8080"])
    end

    subgraph Lomax["DOCKER COMPOSE · red lomax_net"]
        Proxy["<b>proxy</b> nginx :80<br/>único puerto al host 8080"]
        Front["<b>frontend</b> nginx<br/>3 vistas"]
        Back["<b>backend</b> Flask :3000<br/>7 endpoints"]
        Tools["<b>tools</b><br/>aws cli + psql"]
        User -->|"HTTP"| Proxy
        Proxy -->|"/"| Front
        Proxy -->|"/api/"| Back
    end

    subgraph Floci["FLOCI :4566 + hijos Docker"]
        S3[("<img src='https://icon.icepanel.io/AWS/svg/Storage/Simple-Storage-Service.svg' width='50'/><br/><b>Amazon S3</b><br/>originales + miniaturas")]
        DDB[("<img src='https://icon.icepanel.io/AWS/svg/Database/DynamoDB.svg' width='50'/><br/><b>DynamoDB</b><br/>atributos")]
        Lam["<img src='https://icon.icepanel.io/AWS/svg/Compute/Lambda.svg' width='50'/><br/><b>AWS Lambda</b><br/>thumbnail 300x300"]
        RDS[("<img src='https://icon.icepanel.io/AWS/svg/Database/RDS.svg' width='50'/><br/><b>Amazon RDS</b><br/>Postgres :7001<br/>PENDIENTE/PUBLICADO")]
        ECR["<img src='https://icon.icepanel.io/AWS/svg/Containers/Elastic-Container-Registry.svg' width='50'/><br/><b>Amazon ECR</b><br/>registry:2"]
        EKS["<img src='https://icon.icepanel.io/AWS/svg/Containers/Elastic-Kubernetes-Service.svg' width='50'/><br/><b>Amazon EKS</b><br/>k3s :650x<br/>3x backend + frontend"]
        Back --> S3
        Back --> DDB
        Back -->|invoke| Lam
        Lam --> S3
        Back --> RDS
        ECR -->|"pull (mirror)"| EKS
        EKS -->|"pg :7001<br/>:4566"| Back
    end

    classDef client fill:#F8F9FA,stroke:#232F3E,stroke-width:2px,color:#232F3E;
    classDef app fill:#FFFFFF,stroke:#FF9900,stroke-width:2px,color:#232F3E;
    classDef aws fill:#FFFFFF,stroke:#00A4A6,stroke-width:2px,color:#232F3E;
    class User client;
    class Proxy,Front,Back,Tools app;
    class S3,DDB,Lam,RDS,ECR,EKS aws;
```

- Red `lomax_net`, volumen `floci-data`. Solo proxy publica al host (:8080); Floci :4566 publicado solo por el data-plane ECR que usa el daemon.
- EKS k3s real vía Floci (endpoint `https://localhost:6500`). Pods resuelven `floci` por `hostAliases` a `192.168.96.2` (documentado en `infra/eks/deploy.yaml`) porque k3s no ve los alias de Compose.
- Auth EKS con usuario IAM `eks-admin` (el par `test/test` lo rechaza el webhook a propósito).
- ECR con `URI_STYLE=path` porque el daemon solo acepta HTTP en `localhost` literal.
