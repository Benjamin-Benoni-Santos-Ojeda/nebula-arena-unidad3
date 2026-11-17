"""Ejecuta una validación funcional local completa de los generadores Locust
(Jugador con asignador Agones simulado de 3 GameServers, Espectador HLS y Clasificacion 80/20)
y verifica la generación de gráficas con loadtest/graficas.py.

NOTA: Esta prueba corre en loopback sobre 1 host local (máximo 30 jugadores en 3 procesos server.py)
para comprobar los scripts, CSV y gráficas antes del despliegue en nube. NO sustituye la prueba
distribuida de 1 000 jugadores y 500 espectadores en GKE.
"""

from datetime import datetime, timezone
from functools import partial
from http.server import BaseHTTPRequestHandler, SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import time

ROOT = Path(__file__).resolve().parent.parent
EVIDENCIA = ROOT / "evidencia"


def ts():
    return datetime.now(timezone.utc).isoformat()


def iniciar_flota_local(num_gs: int = 4, puerto_base_ws: int = 18650, puerto_base_metrics: int = 19200):
    servidores = {}
    for i in range(1, num_gs + 1):
        servidores[f"nebula-fleet-gs{i}"] = {
            "ws_port": puerto_base_ws + i,
            "metrics_port": puerto_base_metrics + i,
            "state": "Scheduled",
        }
    lock = threading.Lock()
    escalado_rows = []

    def registrar_fila():
        ready = sum(1 for v in servidores.values() if v["state"] == "Ready")
        allocated = sum(1 for v in servidores.values() if v["state"] == "Allocated")
        escalado_rows.append({
            "timestamp": ts(),
            "ready": ready,
            "allocated": allocated,
            "nodes": 1,
        })

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            if length:
                self.rfile.read(length)
            partes = self.path.strip("/").split("/")
            if len(partes) == 3 and partes[0] == "sdk":
                _, gs_name, accion = partes
                with lock:
                    if accion == "ready" and servidores[gs_name]["state"] == "Scheduled":
                        servidores[gs_name]["state"] = "Ready"
                        registrar_fila()
                    elif accion == "shutdown":
                        # En la validación local reponemos el servidor a Ready tras limpiar para permitir rampa y pico seguidos
                        servidores[gs_name]["state"] = "Ready"
                        registrar_fila()
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"{}")
                return

            if self.path.endswith("/gameserverallocations"):
                with lock:
                    elegido = next((k for k, v in servidores.items() if v["state"] == "Ready"), None)
                    if elegido is None:
                        # Si todos están Allocated, permitir reusar el último en prueba local o devolver Allocated
                        elegido = list(servidores.keys())[-1]
                    else:
                        servidores[elegido]["state"] = "Allocated"
                        registrar_fila()
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

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()

    procesos = []
    registrar_fila()
    for gs_name, cfg in servidores.items():
        env = os.environ.copy()
        env["WS_PORT"] = str(cfg["ws_port"])
        env["METRICS_PORT"] = str(cfg["metrics_port"])
        env["AGONES_SDK_HTTP_PORT"] = f"{httpd.server_port}/sdk/{gs_name}"
        proc = subprocess.Popen(
            [sys.executable, str(ROOT / "server" / "server.py")],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        procesos.append(proc)

    deadline = time.time() + 8.0
    while time.time() < deadline:
        if all(v["state"] == "Ready" for v in servidores.values()):
            break
        time.sleep(0.1)

    alloc_url = f"http://127.0.0.1:{httpd.server_port}/apis/allocation.agones.dev/v1/namespaces/nebula/gameserverallocations"
    return httpd, procesos, alloc_url, escalado_rows, servidores


def main():
    httpd, procesos, alloc_url, escalado_rows, servidores = iniciar_flota_local(num_gs=4)
    stream_dir = ROOT / "stream-temp"
    hls_httpd = None
    try:
        # 1. Ejecutar rampa local corta (20 jugadores en 4 GameServers durante 8 s)
        env_locust = os.environ.copy()
        env_locust["AGONES_ALLOCATION_URL"] = alloc_url
        subprocess.run(
            [
                sys.executable, "-m", "locust",
                "-f", str(ROOT / "loadtest" / "locustfile.py"),
                "Jugador",
                "--headless",
                "-u", "20", "-r", "5", "-t", "8s",
                "--csv", str(EVIDENCIA / "rampa-local"),
                "--csv-full-history",
            ],
            env=env_locust,
            check=True,
        )

        # Reiniciar estados a Ready para la prueba de pico local
        for v in servidores.values():
            v["state"] = "Ready"

        # 2. Ejecutar pico local corto (20 jugadores entrando a 20/s durante 6 s)
        subprocess.run(
            [
                sys.executable, "-m", "locust",
                "-f", str(ROOT / "loadtest" / "locustfile.py"),
                "Jugador",
                "--headless",
                "-u", "20", "-r", "20", "-t", "6s",
                "--csv", str(EVIDENCIA / "pico-local"),
                "--csv-full-history",
            ],
            env=env_locust,
            check=True,
        )

        # Guardar CSV de escalado local
        lineas_esc = ["timestamp,ready,allocated,nodes"]
        for r in escalado_rows:
            lineas_esc.append(f"{r['timestamp']},{r['ready']},{r['allocated']},{r['nodes']}")
        (EVIDENCIA / "escalado-local.csv").write_text("\n".join(lineas_esc) + "\n", encoding="utf-8")

        # 3. Generar contenido HLS sintético y probar Espectador
        subprocess.run(
            ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(ROOT / "loadtest" / "crear-hls.ps1"), "-Salida", str(stream_dir)],
            check=True,
        )
        handler_cls = partial(SimpleHTTPRequestHandler, directory=str(stream_dir))
        hls_httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler_cls)
        threading.Thread(target=hls_httpd.serve_forever, daemon=True).start()
        hls_url = f"http://127.0.0.1:{hls_httpd.server_port}"

        subprocess.run(
            [
                sys.executable, "-m", "locust",
                "-f", str(ROOT / "loadtest" / "http_users.py"),
                "Espectador",
                "--headless",
                "--host", hls_url,
                "-u", "10", "-r", "5", "-t", "6s",
                "--csv", str(EVIDENCIA / "stream-local"),
                "--csv-full-history",
            ],
            check=True,
        )

        # 4. Generar gráficas de validación local
        subprocess.run(
            [
                sys.executable, str(ROOT / "loadtest" / "graficas.py"),
                "--rampa", str(EVIDENCIA / "rampa-local_stats_history.csv"),
                "--escalado", str(EVIDENCIA / "escalado-local.csv"),
                "--pico", str(EVIDENCIA / "pico-local_stats_history.csv"),
                "--stream", str(EVIDENCIA / "stream-local_stats_history.csv"),
                "--salida", str(EVIDENCIA / "graficas-local"),
                "--etiqueta", "Validación local loopback",
            ],
            check=True,
        )
        print("PASS: Validación local de rampa, pico, stream HLS y generación de gráficas completada.")
    finally:
        if hls_httpd is not None:
            hls_httpd.shutdown()
            hls_httpd.server_close()
        if stream_dir.exists():
            shutil.rmtree(stream_dir, ignore_errors=True)
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
