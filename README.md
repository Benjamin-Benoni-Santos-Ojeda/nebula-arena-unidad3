# Nebula Arena — Unidad 3

Proyecto integrador de **Infraestructura y despliegue de videojuegos en la nube** (partidas 5 vs 5 en WebSocket a 20 Hz, contenedores Docker, orquestación con Kubernetes y Agones, pipeline CI/CD con identidad federada OIDC, observabilidad con Prometheus y Grafana, pruebas de carga y streaming HLS con Locust, tabla de líderes serverless e infraestructura como código con Terraform).

## Estado del Proyecto

- [x] **3.1 — Bot IA (`bot/`):** Entrenamiento PPO en `CartPole-v1` (`100 352` pasos en CPU = `92.82 s`, recompensa `500.0`, inferencia en 1 hilo = `0.2441 ms` / `4 097.04 dec/s`), dimensionamiento para 2 000 bots a 10 Hz (`5 vCPU` sin margen, `7 vCPU` con +30 % de margen → instancia comercial de `8 vCPU`) y costos en [`evidencia/ppo-dimensionamiento.json`](evidencia/ppo-dimensionamiento.json). Verificación de cuota GPU AWS (`L-DB2E81BA = 0.0 vCPU`) y hardware local en [`evidencia/ppo-cuda-check.txt`](evidencia/ppo-cuda-check.txt).
- [x] **3.2 — Pipeline CI/CD (`.github/workflows/`):** [`ci.yml`](.github/workflows/ci.yml) ejecuta `pytest` (`9/9 PASS`), `verify_agones_allocation.py`, `docker build` + `smoke.py` y `terraform validate`. [`deploy-aws.yml`](.github/workflows/deploy-aws.yml) y [`deploy.yml`](.github/workflows/deploy.yml) publican imagen por SHA en Amazon ECR / Artifact Registry y actualizan `nebula-fleet` con soporte de rollback (`target_sha`).
- [x] **3.3 — Contenedores, ECR y EKS + Agones (`server/`, `k8s/`):** Imagen publicada en `140976191570.dkr.ecr.us-east-2.amazonaws.com/nebula-server` (`:1.0` y `:a1b2c3d`, digest `sha256:ec2691499e979c51f01481e76608a0af408d3058b2204f12913a976f1e6b13ed`, [`evidencia/ecr-push-aws.txt`](evidencia/ecr-push-aws.txt)), flota desplegada en Amazon EKS `nebula-default` (`v1.30`) con Agones `v1.44.0`, asignación `GameServerAllocation` verificada ([`evidencia/eks-gameservers-antes.txt`](evidencia/eks-gameservers-antes.txt), [`evidencia/eks-gameservers-despues.txt`](evidencia/eks-gameservers-despues.txt)) y actualización por SHA con drenado seguro de partida activa ([`evidencia/eks-fleet-update-sha.txt`](evidencia/eks-fleet-update-sha.txt)).
- [x] **3.4 — Autoescalado, carga y streaming HLS (`loadtest/`, `k8s/`):** Ejecución en AWS EKS (`us-east-2`, Modo Reducido por cuota de 32 vCPU: **300 jugadores y 200 espectadores HLS en S3**):
  - Rampa: `32 042` pings con `0.00 %` fallos, RTT mediana `1 ms`, `p95 = 15 ms`, capacidad sostenible medida de **62.5 jugadores por nodo `m7i-flex.large` (2 vCPU)** ([`evidencia/rampa-aws_stats.csv`](evidencia/rampa-aws_stats.csv)).
  - Escalado: `FleetAutoscaler` reacciona en `10–16 s` (hasta `35` GameServers) y el grupo de nodos EC2 escala de `3 a 4` nodos en **`74 s`** ([`evidencia/escalado-aws.csv`](evidencia/escalado-aws.csv), [`evidencia/eks-carga-maxima.txt`](evidencia/eks-carga-maxima.txt)).
  - Pico y Streaming HLS en S3: `28 711` pings en pico (`p95 = 23 ms`) y `2 900` segmentos HLS (`580.1 MB`) con **`0.00 %` rebuffering** (`p95 = 97 ms < 2 000 ms`, [`evidencia/stream-aws_stats.csv`](evidencia/stream-aws_stats.csv)).
  - Gráficas finales generadas en [`evidencia/graficas/rampa-p95.png`](evidencia/graficas/rampa-p95.png), [`evidencia/graficas/escalado.png`](evidencia/graficas/escalado.png) y [`evidencia/graficas/errores.png`](evidencia/graficas/errores.png).
- [x] **3.5 — Tabla de líderes Serverless (`serverless/`):** Desplegada en AWS Lambda (`nebula-leaderboard-default`) + DynamoDB (`nebula-scores`), verificada con `POST /score` y `GET /top` ([`evidencia/clasificacion-aws-smoke.txt`](evidencia/clasificacion-aws-smoke.txt)), carga de **500 usuarios (80/20)** ([`evidencia/clasificacion-aws_stats.csv`](evidencia/clasificacion-aws_stats.csv)) y corte estable ([`evidencia/clasificacion-aws-estable_stats.csv`](evidencia/clasificacion-aws-estable_stats.csv)), más telemetría real de **CloudWatch** (`10.0 ConcurrentExecutions`, `Duration p99 = 482.49 ms` en *cold start* vs `390.55 ms` en caliente, [`evidencia/cloudwatch-lambda-metrics.json`](evidencia/cloudwatch-lambda-metrics.json)).
- [x] **3.6 — Infraestructura como Código con Terraform (`infra-aws/` y `infra/`):** Validación local (`terraform validate`), estado remoto en S3 (`nebula-tfstate-140976191570`), `plan` ([`evidencia/terraform-aws-plan.txt`](evidencia/terraform-aws-plan.txt)), `apply` ([`evidencia/terraform-aws-apply.txt`](evidencia/terraform-aws-apply.txt)), `destroy` ([`evidencia/terraform-aws-destroy.txt`](evidencia/terraform-aws-destroy.txt)) e inventario final con **0 recursos activos** ([`evidencia/inventario-post-destroy.txt`](evidencia/inventario-post-destroy.txt)).
- [x] **Entregables finales:** [`Reporte-tecnico.md`](Reporte-tecnico.md), [`Reporte_Tecnico_Nebula_Arena_Unidad3_Benjamin_Santos_25460724.pdf`](Reporte_Tecnico_Nebula_Arena_Unidad3_Benjamin_Santos_25460724.pdf) y [`Guion-presentacion.md`](Guion-presentacion.md).

---

## Ejecución rápida en Windows (Local)

```powershell
python -m venv .venv --system-site-packages
.\.venv\Scripts\python.exe -m pip install -r server\requirements-dev.txt -r serverless\requirements.txt -r loadtest\requirements.txt
.\.venv\Scripts\python.exe -m pytest server\test_server.py serverless\test_main.py serverless\test_lambda.py -v
.\.venv\Scripts\python.exe server\verify_agones_allocation.py
.\.venv\Scripts\python.exe loadtest\ejecutar-validacion-local.py
```

Para regenerar las gráficas de nube a partir de los CSV recolectados en AWS (`us-east-2`):

```powershell
.\.venv\Scripts\python.exe loadtest\graficas.py --rampa evidencia\rampa-aws_stats_history.csv --escalado evidencia\escalado-aws.csv --pico evidencia\pico-aws_stats_history.csv --stream evidencia\stream-aws_stats_history.csv --salida evidencia\graficas --etiqueta "AWS EKS us-east-2 (300 CCU / 200 CCV)"
```
