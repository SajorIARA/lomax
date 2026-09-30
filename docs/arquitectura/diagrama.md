# Diagrama Lomax (desplegado = diagrama)

```mermaid
flowchart TB

    %% ============================================================
    %% CLIENT TIER
    %% ============================================================
    subgraph ClientTier["CAPA CLIENTE"]
        direction LR
        User["<img src='https://cdn-icons-png.flaticon.com/512/847/847969.png' width='50'/><br/><b>Usuario</b>"]
        Dashboard["<img src='https://imgs.search.brave.com/R3vnbkScZlNFy0TM7czDEZQcRCkPCxheAjIaXfb0b_0/rs:fit:500:0:1:0/g:ce/aHR0cHM6Ly9zdGF0/aWMudmVjdGVlenku/Y29tL3N5c3RlbS9y/ZXNvdXJjZXMvdGh1/bWJuYWlscy8wMjAv/ODc4Lzg2Ni9zbWFs/bC9kYXNoYm9hcmQt/aWNvbi1zdHlsZS1m/cmVlLXZlY3Rvci5q/cGc' width='50'/><br/><b>Dashboard Web</b><br/>Generador / Monitoreo"]
        User -->|"Accede"| Dashboard
    end

    %% ============================================================
    %% AWS CLOUD
    %% ============================================================
    subgraph AWS["AWS CLOUD"]
        
        %% CAPA RED / BALANCEO
        subgraph IngressTier["CAPA ENTRADA & BALANCEO"]
            ALB["<img src='https://imgs.search.brave.com/Hy1NGDZN9_iPRvEy63I9lZA7Mtoise_joHC8KscXYxM/rs:fit:860:0:0:0/g:ce/aHR0cHM6Ly9zeW1i/b2xzLmdldHZlY3Rh/LmNvbS9zdGVuY2ls/XzkvMzlfbG9hZC1i/YWxhbmNlci5hZjdk/NDQ5NWJhLnN2Zw' width='55'/><br/><b>Application Load Balancer</b>"]
            TG["<b>Target Group</b><br/>tg-citas"]
            ALB --> TG
        end

        %% CAPA COMPUTO (ECS)
        subgraph ECSCluster["AMAZON ECS CLUSTER"]
            Service["<img src='https://cdn.jsdelivr.net/gh/homarr-labs/dashboard-icons/svg/aws-ecs.svg' width='55'/><br/><b>ECS Service</b><br/>servicio-citas"]
            
            subgraph TasksPool["Tasks Pool (Scale 1 to 5)"]
                direction LR
                T1["Task 1"]
                T2["Task 2"]
                T3["Task 3"]
                T4["Task 4"]
                T5["Task 5"]
            end
            
            Service --- TasksPool
        end

        %% SERVICIOS AUXILIARES
        subgraph Management["GESTIÓN & DESPLIEGUE"]
            direction LR
            ECR["<img src='https://icon.icepanel.io/AWS/svg/Containers/Elastic-Container-Registry.svg' width='45'/><br/><b>Amazon ECR</b><br/>backend-citas"]
            CW["<img src='https://icon.icepanel.io/AWS/svg/Management-Governance/CloudWatch.svg' width='45'/><br/><b>CloudWatch</b>"]
            ASG["<img src='https://icon.icepanel.io/AWS/svg/Management-Governance/Auto-Scaling.svg' width='45'/><br/><b>Auto Scaling</b>"]
            
            CW -->|"Métrica"| ASG
        end

    end

    %% ============================================================
    %% CONEXIONES PRINCIPALES (FLUJO SIMPLIFICADO)
    %% ============================================================
    Dashboard ==>|"HTTP GET /api/hora"| ALB
    
    TG -->|"Balancea peticiones"| TasksPool
    TasksPool -.->|"Respuesta HTTP"| ALB

    ECR -.->|"Pulls Image"| Service
    ASG -->|"Escala Tasks"| Service

    %% ============================================================
    %% ESTILOS
    %% ============================================================
    classDef client fill:#F8F9FA,stroke:#232F3E,stroke-width:2px,color:#232F3E;
    classDef alb fill:#FFFFFF,stroke:#8C4FFF,stroke-width:2px,color:#232F3E;
    classDef compute fill:#FFFFFF,stroke:#FF9900,stroke-width:2px,color:#232F3E;
    classDef aux fill:#FFFFFF,stroke:#00A4A6,stroke-width:2px,color:#232F3E;

    class User,Dashboard client;
    class ALB,TG alb;
    class Service,T1,T2,T3,T4,T5 compute;
    class ECR,CW,ASG aux;
```

- Red `lomax_net`, volumen `floci-data`. Solo proxy publica al host (:8080); Floci :4566 publicado solo por el data-plane ECR que usa el daemon.
- EKS k3s real vía Floci (endpoint `https://localhost:6500`). Pods resuelven `floci` por `hostAliases` a `192.168.96.2` (documentado en `infra/eks/deploy.yaml`) porque k3s no ve los alias de Compose.
- Auth EKS con usuario IAM `eks-admin` (el par `test/test` lo rechaza el webhook a propósito).
- ECR con `URI_STYLE=path` porque el daemon solo acepta HTTP en `localhost` literal.
