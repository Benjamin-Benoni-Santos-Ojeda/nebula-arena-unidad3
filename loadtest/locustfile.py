"""Generador de carga WebSocket para Nebula Arena (local o distribuido con Agones)."""
import json
import os
import random
import time
import uuid
from pathlib import Path
from gevent import Timeout
from gevent.lock import Semaphore
from locust import User, task, constant_pacing
from locust.exception import StopUser
from requests import post
from websocket import create_connection

WS_URL = os.getenv("WS_URL", "ws://127.0.0.1:7654")
ALLOCATOR_API = os.getenv("AGONES_ALLOCATION_URL")
ALLOCATOR_IP = os.getenv("ALLOCATOR_IP")
AGONES_NAMESPACE = os.getenv("AGONES_NAMESPACE", "default")
FLEET_NAME = os.getenv("AGONES_FLEET", "nebula-fleet")

partida = {"url": None, "reservas": 0}
turno = Semaphore()


def _solicitar_servidor_agones():
    """Solicita un GameServer a través de K8s GameServerAllocation API o Agones Allocator Service."""
    if ALLOCATOR_API:
        headers = {}
        verify_k8s = True
        token_path = Path("/var/run/secrets/kubernetes.io/serviceaccount/token")
        ca_path = Path("/var/run/secrets/kubernetes.io/serviceaccount/ca.crt")
        if token_path.exists():
            headers["Authorization"] = f"Bearer {token_path.read_text(encoding='utf-8').strip()}"
        if ca_path.exists():
            verify_k8s = str(ca_path)
        estado = {}
        for Intento in range(int(os.getenv("ALLOCATION_RETRIES", "5"))):
            respuesta = post(
                ALLOCATOR_API,
                timeout=10,
                headers=headers,
                verify=verify_k8s,
                json={
                    "apiVersion": "allocation.agones.dev/v1",
                    "kind": "GameServerAllocation",
                    "spec": {
                        "selectors": [{"matchLabels": {"agones.dev/fleet": FLEET_NAME}}]
                    },
                },
            )
            respuesta.raise_for_status()
            datos = respuesta.json()
            estado = datos.get("status", datos)
            if estado.get("state") == "Allocated":
                break
            time.sleep(1.2)
        if "state" in estado and estado["state"] != "Allocated":
            raise RuntimeError(f"Agones no asignó un servidor: {estado['state']}")
        puerto = next(
            (p["port"] for p in estado["ports"] if p.get("name") == "game"),
            estado["ports"][0]["port"],
        )
        host = estado["address"]
        if os.getenv("PREFER_INTERNAL_IP") == "1" and "addresses" in estado:
            interno = next((a["address"] for a in estado["addresses"] if a.get("type") == "InternalIP"), None)
            if interno:
                host = interno
    elif ALLOCATOR_IP:
        url = f"https://{ALLOCATOR_IP}/gameserverallocation"
        verify = "ca.crt" if Path("ca.crt").exists() and os.getenv("AGONES_VERIFY_TLS", "true").lower() != "false" else False
        cert = ("client.crt", "client.key") if Path("client.crt").exists() and Path("client.key").exists() else None
        respuesta = post(
            url,
            timeout=10,
            cert=cert,
            verify=verify,
            json={
                "namespace": AGONES_NAMESPACE,
                "gameServerSelectors": [{"matchLabels": {"agones.dev/fleet": FLEET_NAME}}],
            },
        )
        respuesta.raise_for_status()
        gs = respuesta.json()
        estado = gs.get("status", gs)
        if not estado.get("address") or not estado.get("ports"):
            raise RuntimeError(f"Respuesta de asignación sin servidor disponible: {gs}")
        puerto = next(
            (p["port"] for p in estado["ports"] if p.get("name") == "game"),
            estado["ports"][0]["port"],
        )
        host = estado["address"]
    else:
        return WS_URL

    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    return f"ws://{host}:{puerto}"


def reservar_partida(environment=None):
    if not ALLOCATOR_API and not ALLOCATOR_IP:
        return WS_URL
    with turno:
        if partida["reservas"] == 0:
            if environment is not None:
                with environment.events.request.measure("WS", "asignacion") as medicion:
                    try:
                        url = _solicitar_servidor_agones()
                    except Exception as exc:
                        medicion["exception"] = exc
                        raise
            else:
                url = _solicitar_servidor_agones()
            partida.update(url=url, reservas=10)
        partida["reservas"] -= 1
        return partida["url"]


class Jugador(User):
    wait_time = constant_pacing(0.1)

    def on_start(self):
        self.id = str(uuid.uuid4())
        self.ws = None
        with self.environment.events.request.measure("WS", "conexion") as resultado:
            try:
                self.ws = create_connection(reservar_partida(self.environment), timeout=5)
            except Exception as exc:
                resultado["exception"] = exc
        if self.ws is None:
            raise StopUser()

    @task
    def mover(self):
        marca = time.time_ns()
        with self.environment.events.request.measure("WS", "ping") as resultado:
            try:
                with Timeout(3, TimeoutError("No se recibió pong")):
                    self.ws.send(json.dumps({"id": self.id, "x": random.random(), "y": random.random()}))
                    self.ws.send(json.dumps({"ping": marca}))
                    while True:
                        mensaje = self.ws.recv()
                        if json.loads(mensaje).get("pong") == marca:
                            resultado["response_length"] = len(mensaje)
                            break
            except Exception as exc:
                resultado["exception"] = exc
        if resultado["exception"] is not None:
            raise StopUser()

    def on_stop(self):
        if self.ws is not None:
            self.ws.close()
