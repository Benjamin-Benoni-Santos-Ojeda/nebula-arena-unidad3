"""Prueba integral local del ciclo de vida Agones (Ready -> Health -> Allocated -> Shutdown)
y asignación de partidas para múltiples GameServers."""

import asyncio
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
from urllib.request import Request, urlopen

import websockets

ROOT = Path(__file__).resolve().parent.parent


def ts():
    return datetime.now(timezone.utc).isoformat()


def main():
    servidores = {
        "nebula-fleet-gs1": {"ws_port": 17654, "metrics_port": 19100, "state": "Scheduled", "health_count": 0, "events": []},
        "nebula-fleet-gs2": {"ws_port": 17655, "metrics_port": 19101, "state": "Scheduled", "health_count": 0, "events": []},
        "nebula-fleet-gs3": {"ws_port": 17656, "metrics_port": 19102, "state": "Scheduled", "health_count": 0, "events": []},
    }
    lock = threading.Lock()
    historial_estados = []

    def registrar_instantanea(motivo: str):
        conteo = {"Ready": 0, "Allocated": 0, "Shutdown": 0, "Scheduled": 0}
        for s in servidores.values():
            conteo[s["state"]] = conteo.get(s["state"], 0) + 1
        historial_estados.append({
            "timestamp": ts(),
            "motivo": motivo,
            "ready": conteo["Ready"],
            "allocated": conteo["Allocated"],
            "shutdown": conteo["Shutdown"],
            "gameservers": {k: v["state"] for k, v in servidores.items()},
        })

    class AgonesMockHandler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            if length:
                self.rfile.read(length)
            partes = self.path.strip("/").split("/")
            if len(partes) == 3 and partes[0] == "sdk":
                _, gs_name, accion = partes
                with lock:
                    info = servidores[gs_name]
                    if accion == "health":
                        info["health_count"] += 1
                    elif accion == "ready":
                        if info["state"] == "Scheduled":
                            info["state"] = "Ready"
                            info["events"].append({"t": ts(), "event": "Ready"})
                            registrar_instantanea(f"{gs_name} -> Ready")
                    elif accion == "shutdown":
                        info["state"] = "Shutdown"
                        info["events"].append({"t": ts(), "event": "Shutdown"})
                        registrar_instantanea(f"{gs_name} -> Shutdown")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b"{}")
                return

            if self.path.endswith("/gameserverallocations"):
                with lock:
                    elegido = next((k for k, v in servidores.items() if v["state"] == "Ready"), None)
                    if elegido is None:
                        respuesta = {"status": {"state": "UnAllocated"}}
                    else:
                        servidores[elegido]["state"] = "Allocated"
                        servidores[elegido]["events"].append({"t": ts(), "event": "Allocated"})
                        registrar_instantanea(f"{elegido} -> Allocated")
                        respuesta = {
                            "status": {
                                "state": "Allocated",
                                "gameServerName": elegido,
                                "address": "127.0.0.1",
                                "ports": [{"name": "game", "port": servidores[elegido]["ws_port"]}],
                            }
                        }
                cuerpo = json.dumps(respuesta).encode("utf-8")
                self.send_response(201)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(cuerpo)
                return

            self.send_response(404)
            self.end_headers()

        def log_message(self, format, *args):
            return

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), AgonesMockHandler)
    alloc_port = httpd.server_port
    threading.Thread(target=httpd.serve_forever, daemon=True).start()

    procesos = []
    try:
        registrar_instantanea("Inicio de flota (3 réplicas Scheduled)")
        for gs_name, cfg in servidores.items():
            env = os.environ.copy()
            env["WS_PORT"] = str(cfg["ws_port"])
            env["METRICS_PORT"] = str(cfg["metrics_port"])
            env["AGONES_SDK_HTTP_PORT"] = f"{alloc_port}/sdk/{gs_name}"
            proc = subprocess.Popen(
                [sys.executable, str(ROOT / "server" / "server.py")],
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            procesos.append(proc)

        deadline = time.time() + 8.0
        while time.time() < deadline:
            with lock:
                if all(v["state"] == "Ready" for v in servidores.values()):
                    break
            time.sleep(0.1)
        else:
            raise RuntimeError(f"Los GameServers no llegaron a Ready: {servidores}")

        alloc_url = f"http://127.0.0.1:{alloc_port}/apis/allocation.agones.dev/v1/namespaces/nebula/gameserverallocations"
        sala = {"url": None, "reservas": 0}

        def pedir_partida():
            if sala["reservas"] == 0:
                cuerpo = json.dumps({
                    "apiVersion": "allocation.agones.dev/v1",
                    "kind": "GameServerAllocation",
                    "spec": {"selectors": [{"matchLabels": {"agones.dev/fleet": "nebula-fleet"}}]},
                }).encode("utf-8")
                req = Request(alloc_url, data=cuerpo, method="POST", headers={"Content-Type": "application/json"})
                with urlopen(req, timeout=5) as r:
                    estado = json.loads(r.read().decode("utf-8"))["status"]
                assert estado["state"] == "Allocated"
                puerto = next(p["port"] for p in estado["ports"] if p["name"] == "game")
                sala.update(url=f"ws://{estado['address']}:{puerto}", reservas=10)
            sala["reservas"] -= 1
            return sala["url"]

        async def simular_20_jugadores():
            urls_asignadas = [pedir_partida() for _ in range(20)]
            conexiones = [await websockets.connect(u) for u in urls_asignadas]
            rtts_ms = []
            try:
                for idx, ws in enumerate(conexiones):
                    t0 = time.perf_counter()
                    await ws.send(json.dumps({"id": f"p_{idx:02d}", "x": idx * 1.5, "y": idx * 2.0}))
                    await ws.send(json.dumps({"ping": idx}))
                    while True:
                        msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=3))
                        if msg.get("pong") == idx:
                            rtts_ms.append((time.perf_counter() - t0) * 1000.0)
                            break

                metricas_por_gs = {}
                for gs_name, cfg in servidores.items():
                    with urlopen(f"http://127.0.0.1:{cfg['metrics_port']}/metrics", timeout=2) as r:
                        texto = r.read().decode("utf-8")
                    ccu_linea = next(
                        (line for line in texto.splitlines() if line.startswith("nebula_players_connected ")),
                        "nebula_players_connected 0.0",
                    )
                    metricas_por_gs[gs_name] = float(ccu_linea.split()[-1])
                return urls_asignadas, rtts_ms, metricas_por_gs
            finally:
                for ws in conexiones:
                    await ws.close()

        urls_asignadas, rtts_ms, ccu_durante_partida = asyncio.run(simular_20_jugadores())

        assert ccu_durante_partida["nebula-fleet-gs1"] == 10.0
        assert ccu_durante_partida["nebula-fleet-gs2"] == 10.0
        assert ccu_durante_partida["nebula-fleet-gs3"] == 0.0

        deadline = time.time() + 5.0
        while time.time() < deadline:
            with lock:
                if (
                    servidores["nebula-fleet-gs1"]["state"] == "Shutdown"
                    and servidores["nebula-fleet-gs2"]["state"] == "Shutdown"
                ):
                    break
            time.sleep(0.1)
        else:
            raise RuntimeError(f"Los servidores vacíos no transicionaron a Shutdown: {servidores}")

        assert servidores["nebula-fleet-gs3"]["state"] == "Ready"

        evidencia = {
            "resultado": "PASS",
            "fecha_utc": ts(),
            "descripcion": "Verificación local de ciclo de vida Agones (Scheduled -> Ready -> Allocated -> Shutdown) y asignación de 20 jugadores en 3 GameServers (2 Allocated con 10 CCU c/u + 1 Ready en buffer).",
            "ccu_durante_partida": ccu_durante_partida,
            "rtt_ping_promedio_ms": round(sum(rtts_ms) / len(rtts_ms), 3),
            "rtt_ping_max_ms": round(max(rtts_ms), 3),
            "estado_final_gameservers": {
                k: {
                    "state": v["state"],
                    "health_heartbeats": v["health_count"],
                    "events": v["events"],
                }
                for k, v in servidores.items()
            },
            "historial_transiciones": historial_estados,
        }
        out_path = ROOT / "evidencia" / "agones-asignacion-local.json"
        out_path.write_text(json.dumps(evidencia, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps(evidencia, indent=2, ensure_ascii=False))
    finally:
        for proc in procesos:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()
        httpd.shutdown()
        httpd.server_close()


if __name__ == "__main__":
    main()
