# Instrucciones para agentes de programación

Contexto: Unidad 3 del material de estudio de videojuegos en nube. La referencia es Nebula Arena (10 jugadores/partida, WebSocket, métricas y Agones). Priorizar exactitud, ejecutabilidad, código legible y evidencias reales.

1. Antes de editar, leer README.md y PLAN.md.
2. Ejecutar y corregir tests, nunca inventar resultados ni capturas.
3. No crear recursos de nube, cuentas, claves o gastos sin pedir aprobación. Evitar credenciales en Git; usar federación de identidad de GitHub para Google Cloud.
4. Integrar `server/`, `k8s/`, `serverless/`, `loadtest/`, `infra/` y `.github/workflows/`.
5. Escribir scripts reproducibles y documentación de ejecución en Windows.
6. Revisión crítica: comprobar compatibilidad de versiones Agones/Kubernetes/Helm antes del despliegue; asegurar que el servidor transicione Ready, Health y Shutdown según el SDK.
7. Medir CCU, tick p99, RTT p95, nodos, GameServers; separar jugadores reales/simulados de capacidad extrapolada.
8. Los servicios de streaming de video reales no están implementados en esta base; documentar el simulador y su alcance.
