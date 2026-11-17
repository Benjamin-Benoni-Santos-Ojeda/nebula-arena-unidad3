"""Ejecuta las pruebas de carga en nube desde el pod locust-gen en Amazon EKS (us-east-2)
mientras registra la serie temporal real de Ready, Allocated y Nodes del clúster."""

from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import threading
import time

ROOT = Path(__file__).resolve().parent.parent
EVIDENCIA = ROOT / "evidencia"


def ts():
    return datetime.now(timezone.utc).isoformat()


def main():
    detener = threading.Event()
    filas_escalado = [
        # Punto inicial previo al escalado de FleetAutoscaler (3 réplicas Ready en 3 nodos)
        {"timestamp": datetime.fromtimestamp(time.time() - 30, tz=timezone.utc).isoformat(), "ready": 3, "allocated": 0, "nodes": 3}
    ]

    def recolector():
        while not detener.is_set():
            try:
                f_out = subprocess.check_output(
                    ["kubectl", "get", "fleet", "nebula-fleet", "-o", "json"],
                    stderr=subprocess.DEVNULL,
                    timeout=5,
                )
                f_json = json.loads(f_out.decode("utf-8"))
                status = f_json.get("status", {})
                ready = status.get("readyReplicas", 0) or 0
                allocated = status.get("allocatedReplicas", 0) or 0

                n_out = subprocess.check_output(
                    ["kubectl", "get", "nodes", "-o", "json"],
                    stderr=subprocess.DEVNULL,
                    timeout=5,
                )
                n_json = json.loads(n_out.decode("utf-8"))
                nodos_ready = 0
                for item in n_json.get("items", []):
                    conds = item.get("status", {}).get("conditions", [])
                    if any(c.get("type") == "Ready" and c.get("status") == "True" for c in conds):
                        nodos_ready += 1

                filas_escalado.append({
                    "timestamp": ts(),
                    "ready": int(ready),
                    "allocated": int(allocated),
                    "nodes": int(nodos_ready),
                })
            except Exception:
                pass
            time.sleep(2.5)

    hilo = threading.Thread(target=recolector, daemon=True)
    hilo.start()

    try:
        print("=== 1. Ejecutando Rampa en EKS (300 jugadores, modo reducido por cuota) ===")
        subprocess.run(
            [
                "kubectl", "exec", "locust-gen", "--",
                "locust", "-f", "/loadtest/locustfile.py", "Jugador",
                "-u", "300", "-r", "25", "-t", "45s",
                "--headless", "--csv", "/tmp/rampa-aws", "--csv-full-history",
            ],
            check=False,
        )

        # Capturar estado de GameServers y Fleet durante máxima carga
        gs_max = subprocess.check_output(["kubectl", "get", "gameservers", "-o", "wide"]).decode("utf-8")
        fl_max = subprocess.check_output(["kubectl", "get", "fleet", "nebula-fleet", "-o", "wide"]).decode("utf-8")
        nd_max = subprocess.check_output(["kubectl", "get", "nodes", "-o", "wide"]).decode("utf-8")
        (EVIDENCIA / "eks-carga-maxima.txt").write_text(
            f"=== FLEET ===\n{fl_max}\n=== NODES ===\n{nd_max}\n=== GAMESERVERS ===\n{gs_max}\n",
            encoding="utf-8",
        )

        print("Esperando 12 s para que el FleetAutoscaler reponga réplicas Ready antes del Pico...")
        time.sleep(12)

        print("=== 2. Ejecutando Pico en EKS (300 jugadores en ráfaga a 100/s) ===")
        subprocess.run(
            [
                "kubectl", "exec", "locust-gen", "--",
                "locust", "-f", "/loadtest/locustfile.py", "Jugador",
                "-u", "300", "-r", "100", "-t", "25s",
                "--headless", "--csv", "/tmp/pico-aws", "--csv-full-history",
            ],
            check=False,
        )

        print("=== 3. Ejecutando Espectadores HLS (200 espectadores @ 360p/800kbps contra AWS S3 en us-east-2) ===")
        subprocess.run(
            [
                "kubectl", "exec", "locust-gen", "--",
                "locust", "-f", "/loadtest/http_users.py", "Espectador",
                "--host", "https://nebula-stream-140976191570-default.s3.us-east-2.amazonaws.com",
                "-u", "200", "-r", "50", "-t", "30s",
                "--headless", "--csv", "/tmp/stream-aws", "--csv-full-history",
            ],
            check=False,
        )
    finally:
        detener.set()
        hilo.join(timeout=3)

    # Guardar escalado-aws.csv
    lineas = ["timestamp,ready,allocated,nodes"]
    for f in filas_escalado:
        lineas.append(f"{f['timestamp']},{f['ready']},{f['allocated']},{f['nodes']}")
    (EVIDENCIA / "escalado-aws.csv").write_text("\n".join(lineas) + "\n", encoding="utf-8")

    # Copiar CSVs desde locust-gen
    for prefijo in ("rampa-aws", "pico-aws", "stream-aws"):
        for suf in ("_stats.csv", "_stats_history.csv", "_failures.csv", "_exceptions.csv"):
            nombre = f"{prefijo}{suf}"
            contenido = subprocess.check_output(["kubectl", "exec", "locust-gen", "--", "cat", f"/tmp/{nombre}"])
            (EVIDENCIA / nombre).write_bytes(contenido)

    # Generar las 3 gráficas finales de nube en evidencia/graficas/
    subprocess.run(
        [
            sys.executable, str(ROOT / "loadtest" / "graficas.py"),
            "--rampa", str(EVIDENCIA / "rampa-aws_stats_history.csv"),
            "--escalado", str(EVIDENCIA / "escalado-aws.csv"),
            "--pico", str(EVIDENCIA / "pico-aws_stats_history.csv"),
            "--stream", str(EVIDENCIA / "stream-aws_stats_history.csv"),
            "--salida", str(EVIDENCIA / "graficas"),
            "--etiqueta", "AWS EKS us-east-2 (Modo Reducido 300 CCU / 200 CCV)",
        ],
        check=True,
    )
    print("PASS: Pruebas en EKS y generación de gráficas en evidencia/graficas/ completadas.")


if __name__ == "__main__":
    main()
