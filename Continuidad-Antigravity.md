# Nebula Arena · continuidad de la Unidad 3

Esta edición parte del ZIP original del chat «Tiempo y tareas del proyecto». Abre esta carpeta en Antigravity y revisa AGENTS.md, PLAN.md, README.md y Reporte-tecnico.md. El código y las evidencias de la práctica 3.1 están en bot/ y evidencia/.

## Matriz de entrega

| Práctica | Implementación que se debe verificar en el ZIP | Evidencia de aceptación |
|---|---|---|
| 3.1 | PPO en CartPole-v1, 100 000 pasos solicitados, CPU y CUDA con igual semilla, inferencia en CPU | Tiempos de ambos entrenamientos, 10 000 inferencias por modelo, decisiones/s de un hilo, vCPU para 2 000 bots a 10 Hz y costo horario con región y fecha |
| 3.2 | GitHub Actions ejecuta pytest, construye y publica imagen etiquetada por commit y actualiza la Fleet en el entorno autorizado | Ejecución verde, etiqueta o digest publicado y Fleet actualizada |
| 3.3 | Servidor, tests, Dockerfile y Fleet con SDK Agones, puertos y recursos explícitos | Salida de docker run, /metrics y GameServers Ready en Kubernetes |
| 3.4 | Asignación de partidas, Locust, streaming HLS, FleetAutoscaler, autoescalado de nodos, PodMonitor y Grafana | CSV de rampa y pico, métricas de escalado, prueba HLS y reporte de 2–3 páginas |
| 3.5 | API serverless con POST /score y GET /top y persistencia compartida entre instancias | URL autorizada, carga de 500 usuarios con mezcla 80/20, concurrencia, efecto de arranque en frío sobre p99 y costo mensual comparado con VM |
| 3.6 | Terraform en infra/, variables por entorno y estado remoto con bloqueo | Plan revisado en PR, clúster operativo, destroy verificado e inventario final |
| Integrador | Repositorio, pipeline, flota, tabla de líderes y tablero de Grafana | CCU, tick p99, servidores por estado y nodos, reporte de hasta 6 páginas y demo de 10 minutos |

## Validación y costos

1. Prueba Python, imagen, API y manifiestos localmente. Registra fecha, versión, comando, código de salida y archivos de evidencia. Confirma que el SDK de Agones marca cada servidor Ready y que se puede asignar una partida antes de ejecutar Locust.
2. Ejecuta rampa de 1 000 jugadores a 2/s durante 20 min y pico de 1 000 a 50/s durante 10 min tras autorización del entorno. Mide CCU vs p95 con referencia de 80 ms, errores, Ready/Allocated y nodos en una línea de tiempo común. Registra el intervalo entre aumento de demanda y disponibilidad de capacidad. Divide la concurrencia sostenible entre los nodos que efectivamente alojaron partidas. Documenta las condiciones de la medición y el comportamiento del generador de carga.
3. Durante cinco minutos prueba 500 espectadores a 360p de 800 kbps. Reporta segmentos fallidos, rebuffering y bytes transferidos. Para 20 000 espectadores a 6 Mbps, el cálculo nominal es 54 TB decimales por hora, con el costo estimado según la tarifa regional de salida. El PDF admite una variante de 300 jugadores y 200 espectadores cuando hay poca cuota. Registra cuál se ejecutó.
4. Antes de habilitar el despliegue, acuerda nube, región, cuenta y límite de gasto. Revisa cuotas, configura alertas de presupuesto, límites de nodos e instancias serverless, y estima cómputo, egress, IP, balanceador, almacenamiento y monitoreo. Las alertas de presupuesto avisan y el gasto puede seguir acumulándose. Revisa el plan antes de aplicar. Mantén autenticados el despliegue y los endpoints que escriben datos. Tras recopilar evidencias, revisa y ejecuta la destrucción autorizada y comprueba el inventario, incluidos recursos creados fuera del estado de Terraform.

## Bot PPO

Instala gymnasium y stable-baselines3 en un entorno virtual. Para comparar GPU, usa un entorno con PyTorch CUDA y verifica que detecte la GPU.

```powershell
python bot/bot_ppo.py --device cpu --output evidencia/ppo
python bot/bot_ppo.py --device cuda --output evidencia/ppo
```

Cada ejecución guarda el modelo y un JSON. La estimación de vCPU redondea hacia arriba 20 000 decisiones/s entre las decisiones/s medidas con un hilo. Presupuesta margen para el resto del servidor. Para la tabla de costos, multiplica la capacidad aprovisionada por la tarifa de la configuración elegida y anota fuente, región y fecha.

## Reporte y demo

Dedica el reporte a arquitectura y revisión de despliegue, resultados CPU/GPU, tres gráficas de carga, capacidad y escalado, costos por hora y por jugador, y recomendaciones respaldadas por mediciones. En la demo de 10 minutos reserva 2 minutos para arquitectura y pipeline, 5 para demostrar el cambio de capacidad en vivo y 3 para resultados, costos y cierre. Incorpora las capturas al obtenerlas durante las ejecuciones.
