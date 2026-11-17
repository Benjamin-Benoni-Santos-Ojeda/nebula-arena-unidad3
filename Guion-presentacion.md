---
marp: true
theme: default
paginate: true
title: "Nebula Arena · Demostración Técnica (10 minutos)"
---

# Nebula Arena · Infraestructura y Despliegue en la Nube
### Unidad 3 · Demostración Técnica de 10 Minutos

- **Alumno:** Benjamin Benoni Santos Ojeda (`25460724`) · **Docente:** M.C. Omar Joel
- **Entorno ejecutado:** AWS (`140976191570`, región `us-east-2` Ohio) con Terraform, Amazon ECR, Amazon EKS (`v1.30`) + Agones (`v1.44.0`), AWS Lambda + DynamoDB y Amazon S3.
- **Distribución de la demo (10 min):**
  - **Min 0:00 – 2:00 (2 min):** Arquitectura desplegada, CI/CD, imagen por SHA en ECR y drenado seguro en Agones.
  - **Min 2:00 – 7:00 (5 min):** Demostración de asignación de partidas, escalado de flota/nodos y gráficas reales de carga (300 CCU y 200 espectadores HLS).
  - **Min 7:00 – 10:00 (3 min):** Bot PPO (3.1), Serverless 80/20 en Lambda + DynamoDB (3.5), costos por jugador, extrapolación a 20 000 espectadores y destrucción con Terraform (3.6).

---

## Diapositiva 1 · Arquitectura Desplegada en AWS (`us-east-2`) (Min 0:00 – 1:00)

- **Plano de partidas con estado (`server/`, `k8s/`, `infra-aws/eks.tf`):**
  - Clúster **Amazon EKS (`nebula-default`, `v1.30`)** con grupo de nodos `nebula-nodes` (`m7i-flex.large`, elegibles en Free Tier) y **Agones `v1.44.0`**.
  - Cada pod `GameServer` aloja **1 partida de hasta 10 jugadores** (`ws://:7654`, 20 ticks/s) y expone métricas Prometheus (`:9100/metrics`).
- **Servicios sin estado, streaming e IaC:**
  - **Tabla de líderes (`serverless/lambda_function.py`):** **AWS Lambda** (`nebula-leaderboard-default`) + **Amazon DynamoDB** (`nebula-scores`).
  - **Streaming HLS (`infra-aws/stream.tf`):** Manifiesto `360p.m3u8` y 30 segmentos TS CBR de `2 s` a `800 kbps` (`200 KB`) en **Amazon S3**.
  - **Terraform (`infra-aws/`):** Estado remoto en S3 (`s3://nebula-tfstate-140976191570`), `plan`, `apply` y `destroy` verificados.

---

## Diapositiva 2 · CI/CD, Publicación por SHA en ECR y Drenado (Min 1:00 – 2:00)

- **Pipeline CI/CD (`.github/workflows/ci.yml` y `deploy-aws.yml`):**
  1. Ejecuta **9 pruebas unitarias con `pytest`** (`server`, `serverless`, `lambda_function`) y `verify_agones_allocation.py`.
  2. Construye la imagen, ejecuta `server/smoke.py` y publica en **Amazon ECR**:
     - `140976191570.dkr.ecr.us-east-2.amazonaws.com/nebula-server:a1b2c3d`
     - Digest: `sha256:ec2691499e979c51f01481e76608a0af408d3058b2204f12913a976f1e6b13ed` ([`evidencia/ecr-push-aws.txt`](evidencia/ecr-push-aws.txt)).
- **Actualización de Fleet sin cortar partidas ([`evidencia/eks-fleet-update-sha.txt`](evidencia/eks-fleet-update-sha.txt)):**
  - Al aplicar `kubectl patch fleet nebula-fleet` con la imagen `:a1b2c3d`, el servidor con partida en curso (`nebula-fleet-525f8-99mhz`, `Allocated` en `3.144.17.45:7298`) **permaneció activo**, mientras los 2 servidores `Ready` se reemplazaron por el nuevo `GameServerSet` (`5ztfz`).
  - Al terminar la partida en `99mhz`, el servidor invocó `/shutdown` y se drenó limpiamente.

---

## Diapositiva 3 · Asignación de Partidas y Escalado en EKS (Min 2:00 – 4:30)

- **Antes y después de `GameServerAllocation` ([`evidencia/eks-gameservers-antes.txt`](evidencia/eks-gameservers-antes.txt), [`evidencia/eks-gameservers-despues.txt`](evidencia/eks-gameservers-despues.txt)):**
  - Inicialmente: 3 réplicas en estado `Ready` (`7298`, `7825`, `7150`).
  - Tras `GameServerAllocation`: `nebula-fleet-525f8-99mhz` pasa a `Allocated` (`3.144.17.45:7298`) y `FleetAutoscaler` mantiene el buffer de servidores `Ready`.
- **Reacción del autoescalado durante la carga ([`evidencia/graficas/escalado.png`](evidencia/graficas/escalado.png), [`evidencia/escalado-aws.csv`](evidencia/escalado-aws.csv)):**
  - **Capa de partidas (`FleetAutoscaler`):** Reacciona en **10 a 16 segundos** por ciclo, escalando la flota de `3` hasta **`35` GameServers** (`25 Allocated` + `10 Ready` en rampa y `32 Ready` en reposición).
  - **Capa de nodos (EC2 Auto Scaling Group):** Escala de **3 a 4 nodos `m7i-flex.large`**; el cuarto nodo (`ip-10-42-2-138`) tardó **74 segundos** en reportar `Ready`.

---

## Diapositiva 4 · Curva CCU vs. Latencia p95 y Capacidad Real (Min 4:30 – 7:00)

- **Resultados en AWS EKS (`us-east-2`, Modo Reducido por cuota: 300 CCU y 200 espectadores):**
  - **Rampa ([`evidencia/graficas/rampa-p95.png`](evidencia/graficas/rampa-p95.png), [`evidencia/rampa-aws_stats.csv`](evidencia/rampa-aws_stats.csv)):**
    - `32 042` mensajes `ping` con **0.00 % de errores**.
    - De **25 a 250 jugadores**, el RTT p95 se mantiene en **0 – 5 ms** (meta $< 80\text{ ms}$).
    - Entre **260 y 300 jugadores**, al alcanzarse el tope de pods por nodo (`29 pods/nodo` en `m7i-flex.large`), el RTT p95 sube a **15 – 62 ms** (`p95 global = 15 ms`, `p99 = 67 ms`).
    - **Capacidad sostenible medida:** **250 jugadores en 4 nodos = 62.5 jugadores/nodo `m7i-flex.large` (2 vCPU)** (equivalente a **125 jugadores/nodo** de 4 vCPU).
  - **Pico y Streaming HLS ([`evidencia/graficas/errores.png`](evidencia/graficas/errores.png), [`evidencia/stream-aws_stats.csv`](evidencia/stream-aws_stats.csv)):**
    - **Pico (300 jugadores a 100/s):** `28 711` pings con `0 %` error (`p95 = 23 ms`) y `0.014 %` de fallo global al agotarse el buffer inicial en el segundo 17.
    - **Streaming HLS (200 espectadores en `us-east-2`):** `2 900` manifiestos y `2 900` segmentos TS (`580.1 MB` transferidos) con **0.00 % de fallos y 0.00 % de rebuffering** (`p95 = 97 ms < 2 000 ms`).

---

## Diapositiva 5 · Bot PPO (3.1) y Serverless 80/20 en Lambda + DynamoDB (3.5) (Min 7:00 – 8:30)

- **Práctica 3.1 — Bot IA (`CartPole-v1`, [`evidencia/ppo-cpu.json`](evidencia/ppo-cpu.json), [`evidencia/ppo-dimensionamiento.json`](evidencia/ppo-dimensionamiento.json)):**
  - `100 352` pasos en CPU en **92.82 s**, recompensa **500.0 ± 0.0**.
  - Inferencia en 1 hilo: **0.2441 ms** (**4 097.04 decisiones/s**).
  - **2 000 bots a 10 Hz (`20 000 dec/s`):** requieren **5 vCPU** sin margen y **7 vCPU con +30 % de margen** $\implies$ instancia de **8 vCPU** (`c7i.2xlarge` a **\$0.357/h**).
- **Práctica 3.5 — Serverless (`nebula-leaderboard-default` + DynamoDB `nebula-scores`):**
  - URL probada: `https://src4lpfrrkx2ab2eygu656xria0oxyhj.lambda-url.us-east-2.on.aws/` ([`evidencia/clasificacion-aws-smoke.txt`](evidencia/clasificacion-aws-smoke.txt)).
  - **Métricas CloudWatch ([`evidencia/cloudwatch-lambda-metrics.json`](evidencia/cloudwatch-lambda-metrics.json)):** Escaló de `0` a **`10.0 ConcurrentExecutions`** (límite de concurrencia de cuenta nueva); el *cold start* elevó el **`Duration p99` a `482.49 ms`** en el primer minuto, bajando a **`390.55 ms`** en caliente.
  - **Costo mensual (5M req/mes):** **≈ \$0.80 USD/mes** en Lambda (capa gratuita cubre 1M req y 400 000 GB-s) vs. **\$15.18 USD/mes** de una VM `t3.small` 24/7.

---

## Diapositiva 6 · Costos, Extrapolación a 20 000 Espectadores y Limpieza (Min 8:30 – 10:00)

- **Extrapolación de Streaming (20 000 espectadores @ 1080p / 6 000 kbps durante 1 h) [EXTRAPOLADO]:**
  $$\text{Egress} = \frac{20\,000 \times 6\,000 \times 3\,600}{8 \times 10^6} = \mathbf{54\,000\text{ GB (54 TB/h)}} \implies \textbf{USD 2 160 – 4 590 / hora en CDN}$$
- **Costo horario medido de la plataforma:**
  - 4 nodos `m7i-flex.large` (\$0.4032/h) + EKS Control Plane (\$0.10/h) = **\$0.5032 USD / hora** (cubierto 100 % por créditos Free Tier = **\$0.00 USD cobrados**).
  - **Costo por jugador concurrente sostenible (250 CCU):** **\$0.00201 USD / jugador / hora**.
- **Recomendaciones y Limpieza con Terraform (3.6):**
  - Activar delegación de prefijos IPv4 (`ENABLE_PREFIX_DELEGATION=true`) en EKS para elevar el límite de 29 a 110 pods por nodo, y usar escalado predictivo ante picos más rápidos que los **74 s** de arranque de nodo EC2.
  - Ejecución verificada de `terraform destroy` ([`evidencia/terraform-aws-destroy.txt`](evidencia/terraform-aws-destroy.txt)) e inventario post-destroy con **0 recursos activos** ([`evidencia/inventario-post-destroy.txt`](evidencia/inventario-post-destroy.txt)).
