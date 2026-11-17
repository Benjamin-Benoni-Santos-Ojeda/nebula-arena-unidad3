"""Calcula dimensionamiento (2 000 bots a 10 Hz) y costos estimados a partir de evidencia/ppo-*.json."""

import argparse
import json
import math
from datetime import date
from pathlib import Path


# Tarifas públicas de referencia (USD/hora bajo demanda y Spot, consultadas para us-central1 y us-east-1)
TARIFAS_REFERENCIA = {
    "fecha_consulta": "2026-11-16",
    "fuentes": [
        "Google Cloud Compute Engine Pricing (us-central1)",
        "AWS EC2 On-Demand & Spot Pricing (us-east-1)",
    ],
    "inferencia_cpu_8vcpu": [
        {
            "nube": "Google Cloud",
            "region": "us-central1",
            "instancia": "e2-standard-8 (8 vCPU, 32 GB)",
            "vcpu": 8,
            "usd_hora_ondemand": 0.2680,
            "usd_mes_730h": round(0.2680 * 730, 2),
        },
        {
            "nube": "Google Cloud",
            "region": "us-central1",
            "instancia": "c3-highcpu-8 (8 vCPU, 16 GB, optimizada a cómputo)",
            "vcpu": 8,
            "usd_hora_ondemand": 0.3488,
            "usd_mes_730h": round(0.3488 * 730, 2),
        },
        {
            "nube": "AWS",
            "region": "us-east-1",
            "instancia": "c7i.2xlarge (8 vCPU, 16 GB, optimizada a cómputo)",
            "vcpu": 8,
            "usd_hora_ondemand": 0.3570,
            "usd_mes_730h": round(0.3570 * 730, 2),
        },
    ],
    "entrenamiento_gpu": [
        {
            "nube": "Google Cloud",
            "region": "us-central1",
            "instancia": "g2-standard-4 (1x NVIDIA L4, 4 vCPU, 16 GB)",
            "usd_hora_ondemand": 0.7066,
            "usd_hora_spot_aprox": 0.2826,
        },
        {
            "nube": "AWS",
            "region": "us-east-1",
            "instancia": "g6.xlarge (1x NVIDIA L4, 4 vCPU, 16 GB)",
            "usd_hora_ondemand": 0.8048,
            "usd_hora_spot_aprox": 0.3219,
        },
    ],
}


def calcular_dimensionamiento(ppo_data: dict, bots: int = 2000, hz: int = 10, margen: float = 0.30) -> dict:
    demanda_decisiones_s = bots * hz
    cap_hilo = ppo_data["decisions_per_second_single_thread"]
    vcpu_exactas = demanda_decisiones_s / cap_hilo
    vcpu_sin_margen = math.ceil(vcpu_exactas)
    vcpu_con_margen_exacto = math.ceil(vcpu_exactas * (1.0 + margen))
    vcpu_con_margen_sobre_entero = math.ceil(vcpu_sin_margen * (1.0 + margen))
    # Instancias de nube se comercializan en potencias de 2 (2, 4, 8, 16 vCPU)
    vcpu_instancia_comercial = 8 if vcpu_con_margen_sobre_entero <= 8 else math.ceil(vcpu_con_margen_sobre_entero / 2) * 2

    return {
        "bots_activos": bots,
        "frecuencia_hz": hz,
        "demanda_decisiones_por_segundo": demanda_decisiones_s,
        "latencia_media_inferencia_cpu_ms": round(ppo_data["cpu_inference_mean_ms"], 4),
        "decisiones_por_segundo_1_hilo": round(cap_hilo, 2),
        "vcpu_exactas_requeridas": round(vcpu_exactas, 3),
        "vcpu_minimas_sin_margen": vcpu_sin_margen,
        "margen_operativo_pct": int(margen * 100),
        "vcpu_con_margen_30pct": vcpu_con_margen_sobre_entero,
        "vcpu_instancia_recomendada": vcpu_instancia_comercial,
        "holgura_efectiva_en_8vcpu_pct": round((8 * cap_hilo - demanda_decisiones_s) / demanda_decisiones_s * 100, 1),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidencia", type=Path, default=Path("evidencia"))
    args = parser.parse_args()

    archivos = sorted(args.evidencia.glob("ppo-*.json"))
    modelos = {}
    for p in archivos:
        if p.name == "ppo-dimensionamiento.json":
            continue
        data = json.loads(p.read_text(encoding="utf-8"))
        if "training_device" in data:
            modelos[data["training_device"]] = data

    if "cpu" not in modelos:
        raise SystemExit("No se encontró evidencia/ppo-cpu.json")

    dim_cpu = calcular_dimensionamiento(modelos["cpu"])
    resumen = {
        "modelos_medidos": modelos,
        "cuda_disponible_en_host_local": "cuda" in modelos,
        "nota_cuda": (
            "Comparación GPU completada."
            if "cuda" in modelos
            else "El host local Windows 11 cuenta con GPU integrada AMD Radeon 660M y PyTorch 2.12.0+cpu sin soporte CUDA. "
                 "En CartPole-v1 (red MLP pequeña de 2 capas de 64 neuronas y 1 entorno secuencial), la sobrecarga de transferencia "
                 "CPU↔GPU domina sobre el cómputo matricial, por lo que CPU suele igualar o superar a GPU en tiempo de entrenamiento."
        ),
        "dimensionamiento_2000_bots_10hz": dim_cpu,
        "costos_estimados": TARIFAS_REFERENCIA,
    }

    out_json = args.evidencia / "ppo-dimensionamiento.json"
    out_json.write_text(json.dumps(resumen, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(resumen, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
