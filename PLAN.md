# Hoja de ruta de la Unidad 3

## 1. Bot IA (3.1)
Entrenar PPO en CartPole-v1 con CPU y GPU (si hay acceso), registrar tiempo, latencia, decisiones/s, dimensionamiento 2,000 bots a 10Hz y costo/h. Añadir notebook reproducible.

## 2. Servidor y orquestación (3.3)
Validar `server/`, Docker, publicación, GKE, Agones, `Fleet`, asignar GameServer. Evidencias: `docker run`, `/metrics`, `kubectl get gameservers` antes/después.

## 3. CI/CD (3.2)
Completar el workflow con auth OIDC GCP, Artifact Registry, push con SHA y actualización controlada de flota. Evidencias pipeline verde, imagen y rollback.

## 4. Observabilidad y escalado (3.4)
Instalar Prometheus/Grafana, comprobar PodMonitor y métricas; usar Locust remoto en región del clúster y allocator, obtener rampa y pico con 1000 jugadores y 500 espectadores; incluir versión reducida por cuota. No usar 1000 usuarios sobre localhost.

## 5. Serverless (3.5)
Desplegar leaderboard Flask/Firestore en Cloud Run, GET/POST y carga 80/20, registrar URL y métricas de concurrencia.

## 6. Terraform (3.6)
Crear infraestructura GCP segura y con estado remoto, `plan`, `apply` y `destroy`. No ejecutar sin presupuesto, habilitación y credenciales confirmadas.

## Entrega final
Repositorio, CI/CD verde, Grafana, pruebas y curva CCU/latencia, reporte <= 6 páginas, presentación de 10 minutos. No declarar resultados no medidos.
