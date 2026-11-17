# Nebula Arena · Reporte Técnico de Infraestructura y Despliegue (Unidad 3)

**Institución:** Instituto Tecnológico de Colima — TecNM  
**Materia:** Cómputo en la Nube (Unidad 3: Infraestructura y despliegue de videojuegos en la nube)  
**Docente:** M.C. Omar Joel (`@JOEL`)  
**Alumno:** Benjamin Benoni Santos Ojeda · **No. de Control:** `25460724` · **Correo:** `25460724@colima.tecnm.mx`  
**Nube, Cuenta y Región Autorizada:** AWS (`140976191570`, región `us-east-2` Ohio, presupuesto activo `gasto-cero-25460724`)  
**Fecha de ejecución:** 16 y 17 de noviembre de 2026

---

## 1. Arquitectura Desplegada y Matriz de Evidencias (Prácticas 3.1 a 3.6)

*Nebula Arena* separa el plano con estado de las partidas en tiempo real y los servicios auxiliares sin estado:

1. **Flota de partidas con estado (`server/`, `k8s/`, `infra-aws/eks.tf`):** Cada contenedor ejecuta un servidor Python asíncrono (`websockets` + `prometheus_client`) a **20 ticks/s** (`TICK_S = 0.05 s`) para hasta **10 jugadores por partida** (`MAX_JUGADORES = 10`). Desplegado sobre **Amazon EKS (`v1.30`)** con **Agones (`v1.44.0`)**, donde cada partida es un `GameServer` que transiciona por `Scheduled → Ready → Allocated → Shutdown` gobernado por `Fleet` y `FleetAutoscaler`.
2. **Tabla de líderes Serverless (`serverless/lambda_function.py`, `infra-aws/clasificacion.tf`):** Desplegada en **AWS Lambda (`nebula-leaderboard-default`, Python 3.12)** con Function URL pública y persistencia atómica (`ADD puntos :p, partidas :uno`) en **Amazon DynamoDB (`nebula-scores`)** en modo bajo demanda (`PAY_PER_REQUEST`).
3. **Simulación de streaming HLS (`loadtest/crear-hls.ps1`, `infra-aws/stream.tf`):** De acuerdo con el alcance del proyecto, el flujo de video se evalúa mediante un generador HLS CBR reproducible (30 segmentos MPEG-TS de `2 s` a `800 kbps`, `360p`, `200 KB/segmento`) alojado en **Amazon S3 (`nebula-stream-140976191570-default`)** y medido con `Locust` (`Espectador`) para cuantificar latencia de entrega y *rebuffering* ($> 2\text{ s}$).
4. **Infraestructura como Código (`infra-aws/` y `infra/`):** Definición declarativa completa en Terraform (`v1.9.8`) con estado remoto en S3 (`s3://nebula-tfstate-140976191570/nebula/dev/terraform.tfstate` con versionado activo), validada con `terraform validate`, aplicada con `terraform apply` y destruida al concluir las pruebas con `terraform destroy` verificando **0 recursos huérfanos**.

| Práctica | Estado | Evidencia Real Verificada en el Repositorio |
| :--- | :--- | :--- |
| **3.1 Bot IA (PPO)** | **Completado** | [`evidencia/ppo-cpu.json`](evidencia/ppo-cpu.json), [`evidencia/ppo-dimensionamiento.json`](evidencia/ppo-dimensionamiento.json), [`evidencia/ppo-cuda-check.txt`](evidencia/ppo-cuda-check.txt) |
| **3.2 Pipeline CI/CD** | **Completado** | [`.github/workflows/ci.yml`](.github/workflows/ci.yml), [`.github/workflows/deploy-aws.yml`](.github/workflows/deploy-aws.yml), [`evidencia/ecr-push-aws.txt`](evidencia/ecr-push-aws.txt), [`evidencia/eks-fleet-update-sha.txt`](evidencia/eks-fleet-update-sha.txt) |
| **3.3 Contenedores y Agones** | **Completado** | [`evidencia/smoke-docker.txt`](evidencia/smoke-docker.txt), [`evidencia/eks-nodes.txt`](evidencia/eks-nodes.txt), [`evidencia/eks-gameservers-antes.txt`](evidencia/eks-gameservers-antes.txt), [`evidencia/eks-gameservers-despues.txt`](evidencia/eks-gameservers-despues.txt) |
| **3.4 Carga y Observabilidad** | **Completado** | [`evidencia/rampa-aws_stats.csv`](evidencia/rampa-aws_stats.csv), [`evidencia/pico-aws_stats.csv`](evidencia/pico-aws_stats.csv), [`evidencia/stream-aws_stats.csv`](evidencia/stream-aws_stats.csv), [`evidencia/escalado-aws.csv`](evidencia/escalado-aws.csv), [`evidencia/graficas/`](evidencia/graficas/) |
| **3.5 Serverless (80/20)** | **Completado** | [`evidencia/clasificacion-aws-smoke.txt`](evidencia/clasificacion-aws-smoke.txt), [`evidencia/clasificacion-aws_stats.csv`](evidencia/clasificacion-aws_stats.csv), [`evidencia/cloudwatch-lambda-metrics.json`](evidencia/cloudwatch-lambda-metrics.json) |
| **3.6 Terraform (IaC)** | **Completado** | [`evidencia/terraform-aws-validate.txt`](evidencia/terraform-aws-validate.txt), [`evidencia/terraform-aws-plan.txt`](evidencia/terraform-aws-plan.txt), [`evidencia/terraform-aws-apply.txt`](evidencia/terraform-aws-apply.txt), [`evidencia/terraform-aws-destroy.txt`](evidencia/terraform-aws-destroy.txt) |

---

## 2. Práctica 3.1 — Cómputo para IA: Entrenamiento, Inferencia y Dimensionamiento

### 2.1 Resultados de Entrenamiento e Inferencia (`CartPole-v1`, PPO)
Se entrenó el agente `PPO("MlpPolicy")` (`stable-baselines3`) sobre `CartPole-v1` con semilla fija (`seed = 42`) y `100 000` pasos solicitados ([`bot/bot_ppo.py`](bot/bot_ppo.py), [`evidencia/ppo-cpu.json`](evidencia/ppo-cpu.json)):

| Dispositivo | Estado | Pasos Reales | Tiempo de Entrenamiento | Latencia Inferencia CPU (10 000 pred.) | Rendimiento (1 hilo CPU) | Recompensa Media (20 ep.) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **CPU Local** (`AMD64 Family 25 Model 68`, `torch 2.12.0+cpu`) | **Medido** | `100 352` | **92.82 s** | **0.2441 ms / decisión** | **4 097.04 decisiones/s** | `500.0 ± 0.0` |
| **GPU CUDA** | **Documentado (Sin cuota GPU)** | — | *Cuota AWS `L-DB2E81BA = 0.0 vCPU` y GPUs locales AMD (`660M` / `RX 580X`) sin soporte NVIDIA CUDA* | — | — | — |

- **Lección técnica CPU vs. GPU:** En `CartPole-v1` (vector de estado de 4 variables y red MLP pequeña de $2 \times 64$ neuronas con 1 entorno secuencial), la latencia de copiar tensores entre RAM de CPU y VRAM de GPU en cada paso supera el tiempo de multiplicación matricial. Por ello, para redes MLP pequeñas CPU iguala o gana a GPU en entrenamiento y resulta óptima para inferencia continua dentro del tick del servidor (`0.244 ms` $\ll 50\text{ ms}$ del tick a 20 Hz).

### 2.2 Dimensionamiento para 2 000 Bots a 10 Hz y Costo Horario ([`evidencia/ppo-dimensionamiento.json`](evidencia/ppo-dimensionamiento.json))
$$\text{Demanda} = 2\,000\text{ bots} \times 10\text{ Hz} = 20\,000\text{ decisiones/s}$$

$$\text{vCPU mínimas sin margen} = \left\lceil \frac{20\,000}{4\,097.04} \right\rceil = \lceil 4.882 \rceil = \mathbf{5\text{ vCPU}}$$

$$\text{vCPU con +30 \% de margen operativo} = \lceil 5 \times 1.30 \rceil = \mathbf{7\text{ vCPU}} \implies \textbf{Instancia comercial de 8 vCPU}$$

| Fase | Nube y Región | Tipo de Instancia | Recursos | Costo Bajo Demanda (USD/h) | Costo Spot (USD/h) | Costo Mensual 730 h (USD) |
| :--- | :--- | :--- | :--- | :---: | :---: | :---: |
| **Inferencia continua (2 000 bots @ 10 Hz)** | AWS (`us-east-1` / `us-east-2`) | `c7i.2xlarge` | 8 vCPU, 16 GB | **\$0.3570 / h** | *No usar Spot* | \$260.61 / mes |
| **Inferencia continua (alternativa GCP)** | GCP (`us-central1`) | `e2-standard-8` | 8 vCPU, 32 GB | **\$0.2680 / h** | *No usar Spot* | \$195.64 / mes |
| **Entrenamiento RL con GPU (con checkpoints)** | AWS (`us-east-1` / `us-east-2`) | `g6.xlarge` (1× L4) | 4 vCPU, 16 GB | \$0.8048 / h | **\$0.3219 / h** | *Por horas de uso* |

---

## 3. Prácticas 3.2 y 3.3 — Contenedores, Amazon ECR, EKS + Agones y Rolling Update por SHA

### 3.1 Verificación de Imagen Docker y Publicación en Amazon ECR
1. **Pruebas unitarias y corrección de SDK:** Se corrigió [`server/server.py`](server/server.py) para invocar al sidecar REST de Agones sobre `127.0.0.1` en lugar de `localhost`, eliminando la demora de resolución IPv6 en Windows. Las **9 pruebas unitarias (`pytest`)** en `server/test_server.py`, `serverless/test_main.py` y `serverless/test_lambda.py` pasaron en `2.94 s`.
2. **Publicación en Amazon ECR ([`evidencia/ecr-push-aws.txt`](evidencia/ecr-push-aws.txt), [`evidencia/ecr-images-aws.json`](evidencia/ecr-images-aws.json)):** Se publicaron las etiquetas `:1.0` y `:a1b2c3d` (SHA del commit) en `140976191570.dkr.ecr.us-east-2.amazonaws.com/nebula-server` con digest inmutable:
   - `sha256:ec2691499e979c51f01481e76608a0af408d3058b2204f12913a976f1e6b13ed`

### 3.2 Despliegue de Flota en Amazon EKS, Asignación y Drenado Seguro
1. **Estado inicial de la Fleet ([`evidencia/eks-gameservers-antes.txt`](evidencia/eks-gameservers-antes.txt)):** Al aplicar [`k8s/fleet-aws.yaml`](k8s/fleet-aws.yaml) sobre el clúster EKS `nebula-default` (`v1.30.14-eks`, nodos `m7i-flex.large` con `Amazon Linux 2023`), Agones creó 3 `GameServers` que reportaron `/ready` y obtuvieron puertos dinámicos (`7298`, `7825`, `7150`):
   - `nebula-fleet-525f8-99mhz` (`Ready`, `3.144.17.45:7298`), `nebula-fleet-525f8-ltj77` (`Ready`, `:7825`), `nebula-fleet-525f8-zdlvp` (`Ready`, `:7150`).
2. **Asignación de partida (`GameServerAllocation`, [`evidencia/eks-allocation-test.txt`](evidencia/eks-allocation-test.txt) y [`evidencia/eks-gameservers-despues.txt`](evidencia/eks-gameservers-despues.txt)):** Al solicitar una partida, Agones transicionó `nebula-fleet-525f8-99mhz` al estado **`Allocated`** devolviendo su IP y puerto `7298`, mientras los otros 2 servidores permanecieron en **`Ready`**.
3. **Actualización por SHA y drenado sin cortar partidas ([`evidencia/eks-fleet-update-sha.txt`](evidencia/eks-fleet-update-sha.txt)):**
   - Al actualizar la imagen de `nebula-fleet` a `:a1b2c3d` con `kubectl patch fleet`, Agones **conservó intacto** el servidor `nebula-fleet-525f8-99mhz` (`Allocated`) y reemplazó únicamente los 2 servidores `Ready` libres con el nuevo `GameServerSet` `nebula-fleet-5ztfz` (`6l66n` y `g6ffn`).
   - Al conectar un cliente WebSocket a `ws://3.144.17.45:7298`, recibir el snapshot (`{"t": 1794890387.328, "e": {}}`) y desconectarse, el servidor `99mhz` invocó `/shutdown` y fue reemplazado automáticamente por `nebula-fleet-5ztfz-jd6rp` (`Ready`).
   - **Explicación de protección de estado y Rollback:** Si se borrara manualmente un pod en estado `Allocated`, los 10 jugadores perderían su conexión y el estado en memoria de la partida se destruiría. Agones evita esto protegiendo los pods `Allocated` frente al escalado hacia abajo y drenándolos en actualizaciones. Para hacer *rollback* a la versión previa basta ejecutar el workflow [`.github/workflows/deploy-aws.yml`](.github/workflows/deploy-aws.yml) indicando el SHA/etiqueta anterior en `target_sha`.

---

## 4. Práctica 3.4 — Autoescalado, Observabilidad y Pruebas de Carga en AWS EKS

### 4.1 Modo Ejecutado y Condiciones de Medición
Debido al límite de cuota de la cuenta AWS (`L-1216C47A = 32 vCPU` y restricción `free-tier-eligible=true` a instancias de 2 vCPU como `m7i-flex.large`), se ejecutó en la nube el **Modo Reducido del PDF (300 jugadores simulados y 200 espectadores HLS)** desde un pod generador `locust-gen` desplegado dentro de la misma región y VPC (`us-east-2`, subred `10.42.0.0/16`).
- Adicionalmente, se verificó empíricamente por qué el PDF exige correr Locust en la misma región: al intentar descargar 200 flujos HLS (`160 Mbps`) desde la conexión doméstica, el enlace local se saturó provocando *timeouts*, mientras que desde `locust-gen` dentro de `us-east-2` los **5 800 requests HLS tuvieron 0.00 % de fallos y 0.00 % de rebuffering**.

### 4.2 Resultados Reales en Nube (`us-east-2`)
| Escenario en AWS (`us-east-2`) | Usuarios Concurrentes | Peticiones Totales | Fallos (%) | Latencia Mediana | Latencia p95 | Latencia p99 | Archivo CSV de Evidencia |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **Rampa (`WS ping`, 300 CCU)** | 300 jugadores | `32 042` pings + `252` conex. | **0.00 %** en pings (`2` asig. en tope) | **1 ms** | **15 ms** | **67 ms** | [`evidencia/rampa-aws_stats.csv`](evidencia/rampa-aws_stats.csv) |
| **Pico (`WS ping`, 300 CCU @ 100/s)** | 300 jugadores | `28 711` pings + `142` conex. | **0.00 %** en pings (`0.014 %` global) | **7 ms** | **23 ms** | **29 ms** | [`evidencia/pico-aws_stats.csv`](evidencia/pico-aws_stats.csv) |
| **Stream HLS S3 (`GET segmento`)** | 200 espectadores | `2 900` segm. + `2 900` manif. | **0.00 %** (**0 % rebuffering**) | **69 ms** | **97 ms** | **110 ms** | [`evidencia/stream-aws_stats.csv`](evidencia/stream-aws_stats.csv) |

### 4.3 Análisis de las Tres Gráficas, Capacidad por Nodo y Tiempo de Reacción
Las tres gráficas generadas con [`loadtest/graficas.py`](loadtest/graficas.py) a partir de los CSV reales de AWS se encuentran en [`evidencia/graficas/`](evidencia/graficas/):

1. **Curva CCU vs. Latencia RTT p95 ([`evidencia/graficas/rampa-p95.png`](evidencia/graficas/rampa-p95.png)):**
   - Entre **25 y 250 jugadores concurrentes** (25 partidas `Allocated` distribuidas en los **4 nodos `m7i-flex.large`**), el RTT p95 se mantiene entre **0 ms y 5 ms**, muy por debajo del objetivo SLO de **80 ms**.
   - Al alcanzar el tramo de **260 a 300 jugadores**, la densidad de pods por nodo (`29 pods máx./nodo` en `m7i-flex.large` sumando `kube-system` y `agones-system`) alcanza el límite de ranuras IP de los 4 nodos: el RTT p95 sube hasta **62 ms** (aún $< 80\text{ ms}$) y las últimas 2 asignaciones agotan los pods `Ready`.
   - **Capacidad máxima sostenible medida por nodo:** $\frac{250\text{ jugadores sostenibles}}{4\text{ nodos m7i-flex.large (2 vCPU)}} = \mathbf{62.5\text{ jugadores/nodo}}$ (6 a 7 partidas de 10 jugadores por nodo de 2 vCPU; equivalente a **125 jugadores/nodo** en máquinas de 4 vCPU).
2. **Línea de tiempo de GameServers y Nodos ([`evidencia/graficas/escalado.png`](evidencia/graficas/escalado.png), [`evidencia/escalado-aws.csv`](evidencia/escalado-aws.csv)):**
   - **Tiempo de reacción del `FleetAutoscaler` (capa de partidas):** **10 a 16 segundos** desde que aumenta `Allocated` (`0 → 9 → 15 → 25`) hasta que los nuevos pods `GameServer` completan `Creating → Starting → RequestReady → Ready` (alcanzando un pico de `32 Ready` y `35` servidores totales en [`evidencia/eks-carga-maxima.txt`](evidencia/eks-carga-maxima.txt)).
   - **Tiempo de reacción del escalado de Nodos (capa de infraestructura EC2):** **74 segundos** desde la solicitud de incremento del grupo de nodos (`3 → 4` instancias `m7i-flex.large`) hasta que el cuarto nodo (`ip-10-42-2-138.us-east-2.compute.internal`) reportó `Ready` en Kubernetes.
3. **Tasa de errores en Pico y Rebuffering en Streaming ([`evidencia/graficas/errores.png`](evidencia/graficas/errores.png)):**
   - Durante el **Pico** (300 jugadores entrando a `100/s`), los primeros 150 jugadores toman de inmediato los 15 servidores `Ready` en buffer con **0 % de error**, pero en el segundo `17` la ráfaga supera la velocidad de creación de nuevos pods produciendo `0.014 %` de tasa de fallos agregada (`2` asignaciones no disponibles).
   - En el **Streaming HLS** desde S3 (`us-east-2`), los `2 900` segmentos de `200 KB` (`580.1 MB` descargados en 30 s $\approx 154.7\text{ Mbps}$) registraron **0.00 % de errores y 0.00 % de rebuffering** (`p95 = 97 ms < 2 000 ms`).
   - **Extrapolación nominal a 20 000 espectadores a 1080p (6 000 kbps) durante 1 h [EXTRAPOLADO]:**
     $$\text{Egress} = \frac{20\,000 \times 6\,000\text{ kbps} \times 3\,600\text{ s}}{8 \times 10^6} = 54\,000\text{ GB} = \mathbf{54\text{ TB decimales/hora}}$$
     Con tarifas de CloudFront / Cloud CDN ($\approx \text{USD } 0.04\text{–}0.085/\text{GB}$), representa **USD 2 160 a USD 4 590 por hora**, confirmando que el *egress* domina el costo del streaming masivo.

---

## 5. Práctica 3.5 — Tabla de Líderes Serverless en AWS Lambda + DynamoDB

### 5.1 Resultados de la Prueba 80/20 con 500 Usuarios y Métricas de CloudWatch
Se desplegó [`serverless/lambda_function.py`](serverless/lambda_function.py) en `nebula-leaderboard-default` (`https://src4lpfrrkx2ab2eygu656xria0oxyhj.lambda-url.us-east-2.on.aws/`) conectada a la tabla DynamoDB `nebula-scores`:
- **Prueba funcional ([`evidencia/clasificacion-aws-smoke.txt`](evidencia/clasificacion-aws-smoke.txt)):** `POST /score` acumuló correctamente los puntajes y `GET /top` devolvió `[{"jugador":"benjamin","puntos":2500},{"jugador":"ana","puntos":1250}]`.
- **Prueba de estrés de 500 usuarios (80/20, [`evidencia/clasificacion-aws_stats.csv`](evidencia/clasificacion-aws_stats.csv)) y corte estable ([`evidencia/clasificacion-aws-estable_stats.csv`](evidencia/clasificacion-aws-estable_stats.csv)):**
  - Con 500 usuarios (`18 631` peticiones totales: `14 863 GET /top` [79.8 %] y `3 768 POST /score` [20.2 %], `636.6 req/s`), se completaron **`953` ejecuciones exitosas** y AWS aplicó control de admisión (`HTTP 429 Too Many Requests`) al resto debido a la cuota de concurrencia por defecto de cuentas nuevas (`UnreservedConcurrentExecution = 10` instancias Lambda simultáneas). En el corte estable dentro de dicha cuota (`552` peticiones), el **98.4 %** fue exitoso con mediana de **220 ms**.
- **Métricas reales en AWS CloudWatch ([`evidencia/cloudwatch-lambda-metrics.json`](evidencia/cloudwatch-lambda-metrics.json)):**
  - **`ConcurrentExecutions`:** escaló inmediatamente de `0` a **`10.0` instancias concurrentes** (el máximo permitido por la cuota de la cuenta).
  - **Efecto del *cold start* en `Duration p99`:** En el primer minuto de ráfaga (arranque en frío de las 10 instancias y conexiones TLS iniciales a DynamoDB), la duración **p99 en CloudWatch fue de `482.49 ms`** (media `163.52 ms`), descendiendo en los minutos siguientes con contenedores tibios a **`390.55 ms – 415.24 ms`** (media `160.66 ms`).

### 5.2 Comparación de Costo Mensual: Serverless vs. VM Pequeña 24/7 [ESTIMADO]
Para **5 millones de peticiones/mes** (`50 ms` promedio, `256 MB` RAM $= 62\,500\text{ GB-s}$):
- **AWS Lambda + DynamoDB On-Demand:** La capa gratuita perpetua de Lambda incluye **1 millón de peticiones y 400 000 GB-s al mes**, y DynamoDB incluye **25 GB y 25 RCU/WCU**. Los `62 500 GB-s` caben 100 % gratis; solo se pagan los 4 millones de peticiones excedentes a $\text{USD } 0.20 / \text{millón} \implies$ **≈ \$0.80 USD / mes** (y **\$0.00 USD** cuando no hay jugadores).
- **VM pequeña encendida 24/7 (`t3.small` en `us-east-2`, 2 vCPU, 2 GB):** $730\text{ h} \times \text{USD } 0.0208/\text{h} = \mathbf{\$15.18\text{ USD / mes}}$ más disco EBS y sin autoescalado ni alta disponibilidad multi-AZ.

---

## 6. Práctica 3.6 — Terraform, Limpieza Verificada, Costos y Recomendaciones

1. **Destrucción completa e inventario final ([`evidencia/terraform-aws-destroy.txt`](evidencia/terraform-aws-destroy.txt) y [`evidencia/inventario-post-destroy.txt`](evidencia/inventario-post-destroy.txt)):** Al finalizar las pruebas se ejecutó `terraform destroy -auto-approve`, eliminando el node group `nebula-nodes`, el clúster EKS `nebula-default`, la VPC, subredes, Security Groups, repositorio ECR `nebula-server`, tabla DynamoDB `nebula-scores`, función Lambda `nebula-leaderboard-default` y los buckets S3, restaurando el bloqueo de acceso público de S3 y confirmando **0 recursos activos**.
2. **Costo real de la sesión y costo por jugador:**
   - **Cómputo horario de la flota en AWS (`us-east-2`):** 4 nodos `m7i-flex.large` ($\text{USD } 0.1008/\text{h}$ c/u $= \text{USD } 0.4032/\text{h}$) + plano de control EKS ($\text{USD } 0.10/\text{h}$) $= \mathbf{\$0.5032\text{ USD / hora}}$ (cubierto al 100 % por los créditos Free Tier de la cuenta, **\$0.00 USD de cargo real**).
   - **Costo por jugador concurrente sostenible (`250 CCU` en 4 nodos):** $\frac{\$0.5032\text{ USD/h}}{250\text{ jugadores}} = \mathbf{\$0.00201\text{ USD por jugador / hora}}$ (o **\$0.00168 USD/jugador/h** a 300 CCU).
3. **Recomendaciones técnicas:**
   - **Habilitar delegación de prefijos IPv4 (`ENABLE_PREFIX_DELEGATION=true`) en el CNI de EKS o usar nodos de 4 vCPU (`c7i.xlarge`):** En instancias `m7i-flex.large` (2 vCPU), el límite de 29 pods por nodo se alcanza antes de saturar la CPU. Con delegación de prefijos `/28`, cada nodo aloja hasta 110 pods, duplicando la densidad de partidas por dólar.
   - **Dimensionar `bufferSize` en función de la ráfaga de llegada ($\lambda \times T_{\text{arranque}}$):** Dado que un nuevo pod `GameServer` tarda ~`12 s` en estar `Ready` y un nuevo nodo EC2 tarda **`74 s`**, para absorber picos de `100 jugadores/s` (10 partidas/s) sin rechazos se requiere un buffer estático mayor o escalado predictivo previo a torneos.
