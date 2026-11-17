"""Genera gráficas a partir de CSV guardados durante una ejecución real."""
import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def guardar(figura, salida, nombre):
    figura.tight_layout()
    figura.savefig(salida / nombre, dpi=160)
    plt.close(figura)


def seleccionar_serie(df: pd.DataFrame, preferido: str) -> pd.DataFrame:
    subset = df.loc[df["Name"] == preferido]
    if not subset.empty:
        return subset
    return df.loc[df["Name"] == "Aggregated"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rampa", type=Path, required=True)
    parser.add_argument("--escalado", type=Path, required=True,
                        help="CSV con timestamp,ready,allocated,nodes")
    parser.add_argument("--pico", type=Path, required=True)
    parser.add_argument("--stream", type=Path, required=True)
    parser.add_argument("--salida", type=Path, required=True)
    parser.add_argument("--etiqueta", type=str, default="",
                        help="Sufijo informativo para el título (p. ej. 'Prueba funcional local' o 'GKE us-central1')")
    args = parser.parse_args()
    args.salida.mkdir(parents=True, exist_ok=True)
    sufijo = f" ({args.etiqueta})" if args.etiqueta else ""

    rampa = pd.read_csv(args.rampa)
    ping = seleccionar_serie(rampa, "ping")
    if ping.empty:
        parser.error("No hay filas ping ni Aggregated en el archivo de rampa.")
    fig, ax = plt.subplots(figsize=(7, 4.2))
    ax.plot(ping["User Count"], pd.to_numeric(ping["95%"], errors="coerce"), marker="o", markersize=3, label="RTT p95 medido")
    ax.axhline(80, linestyle="--", color="darkorange", label="Meta SLO p95 = 80 ms")
    ax.set(
        xlabel="Jugadores concurrentes (Usuarios Locust)",
        ylabel="RTT p95 (ms)",
    )
    ax.set_title(f"Curva CCU vs Latencia RTT p95{sufijo}", fontsize=10.5)
    ax.grid(True, alpha=0.3)
    ax.legend()
    guardar(fig, args.salida, "rampa-p95.png")

    escalado = pd.read_csv(args.escalado)
    fig, ax = plt.subplots(figsize=(7, 4.2))
    tiempos = pd.to_datetime(escalado["timestamp"], utc=True)
    for columna in ("ready", "allocated", "nodes"):
        if columna in escalado.columns:
            ax.step(tiempos, escalado[columna], label=columna.capitalize(), where="post", linewidth=1.8)
    ax.set(
        ylabel="Cantidad",
        xlabel="Hora UTC",
    )
    ax.set_title(f"Línea de tiempo de GameServers y Nodos{sufijo}", fontsize=10.5)
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.autofmt_xdate()
    guardar(fig, args.salida, "escalado.png")

    fig, ejes = plt.subplots(2, 1, figsize=(7, 5.5))
    for archivo, nombre, etiqueta, eje in [
        (args.pico, "Aggregated", f"Pico de jugadores: tasa de errores{sufijo}", ejes[0]),
        (args.stream, "segmento", f"Streaming HLS: fallos o rebuffering (>2 s){sufijo}", ejes[1]),
    ]:
        historia = pd.read_csv(archivo)
        datos = seleccionar_serie(historia, nombre)
        if datos.empty:
            parser.error(f"Faltan filas {nombre}/Aggregated en {archivo}")
        segundos = datos["Timestamp"] - datos["Timestamp"].iloc[0]
        divisor = datos["Requests/s"].where(datos["Requests/s"] > 0)
        tasa = (100 * datos["Failures/s"] / divisor).fillna(0.0)
        eje.plot(segundos, tasa, marker=".", linewidth=1.5)
        eje.set(xlabel="Segundos desde el inicio", ylabel="Fallos (%)")
        eje.set_title(etiqueta, fontsize=10.5)
        eje.grid(True, alpha=0.3)
    guardar(fig, args.salida, "errores.png")


if __name__ == "__main__":
    main()
