"""Servidor educativo WebSocket para 10 jugadores por partida.

Expone /metrics en el puerto 9100 y un WebSocket en el 7654.
En Agones, notifica ready/health/shutdown mediante el sidecar SDK.
"""
import asyncio
import json
import os
import time
import logging
import urllib.request

import websockets
from prometheus_client import Gauge, Histogram, start_http_server

MAX_JUGADORES = 10
TICK_S = 0.05
JUGADORES = Gauge("nebula_players_connected", "Jugadores conectados")
TICK = Histogram("nebula_tick_seconds", "Duracion del tick", buckets=(.001, .0025, .005, .01, .025, .05, .1))
estado = {}
conexiones = set()
partida = {"iniciada": False}
SDK_HOST = os.getenv("AGONES_SDK_HTTP_HOST", "127.0.0.1")
SDK_PORT = os.getenv("AGONES_SDK_HTTP_PORT")
WS_PORT = int(os.getenv("WS_PORT", "7654"))
METRICS_PORT = int(os.getenv("METRICS_PORT", "9100"))


def agones(ruta):
    """Petición REST al sidecar; sin sidecar el servidor sigue en modo local."""
    if not SDK_PORT:
        return
    req = urllib.request.Request(
        f"http://{SDK_HOST}:{SDK_PORT}{ruta}", data=b"{}", method="POST",
        headers={"Content-Type": "application/json"},
    )
    urllib.request.urlopen(req, timeout=0.5).close()


async def ciclo_agones():
    if not SDK_PORT:
        return
    listo = False
    while True:
        try:
            await asyncio.to_thread(agones, "/health")
            if not listo:
                await asyncio.to_thread(agones, "/ready")
                listo = True
            if partida["iniciada"] and not conexiones:
                await asyncio.to_thread(agones, "/shutdown")
                return
        except OSError:
            logging.warning("No se pudo contactar el SDK de Agones", exc_info=True)
        await asyncio.sleep(1)


def snapshot():
    return json.dumps({"t": time.time(), "e": estado})


async def jugador(ws):
    if len(conexiones) >= MAX_JUGADORES:
        await ws.close(code=4000, reason="partida llena")
        return
    conexiones.add(ws)
    JUGADORES.set(len(conexiones))
    partida["iniciada"] = True
    mi_id = None
    try:
        async for mensaje in ws:
            try:
                datos = json.loads(mensaje)
            except json.JSONDecodeError:
                continue
            if not isinstance(datos, dict):
                continue
            if "ping" in datos:
                await ws.send(json.dumps({"pong": datos["ping"]}))
            elif isinstance(datos.get("id"), str):
                nuevo_id = datos["id"]
                if mi_id is not None and mi_id != nuevo_id:
                    estado.pop(mi_id, None)
                mi_id = nuevo_id
                estado[mi_id] = datos
    finally:
        conexiones.discard(ws)
        JUGADORES.set(len(conexiones))
        if mi_id is not None:
            estado.pop(mi_id, None)


async def bucle():
    while True:
        inicio = time.perf_counter()
        if conexiones:
            websockets.broadcast(conexiones, snapshot())
        TICK.observe(time.perf_counter() - inicio)
        await asyncio.sleep(TICK_S)


async def main():
    start_http_server(METRICS_PORT)
    async with websockets.serve(jugador, "0.0.0.0", WS_PORT):
        async with asyncio.TaskGroup() as tasks:
            tasks.create_task(ciclo_agones())
            tasks.create_task(bucle())


if __name__ == "__main__":
    asyncio.run(main())

