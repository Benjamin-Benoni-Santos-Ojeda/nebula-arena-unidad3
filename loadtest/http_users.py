import os
import uuid
from urllib.parse import urljoin, urlsplit

from locust import HttpUser, between, constant_pacing, task


class Clasificacion(HttpUser):
    wait_time = between(0.2, 0.5)

    def on_start(self):
        self.jugador = uuid.uuid4().hex
        token = os.getenv("LEADERBOARD_ID_TOKEN")
        if token:
            self.client.headers["Authorization"] = f"Bearer {token}"

    @task(4)
    def consultar(self):
        self.client.get("/top", timeout=5)

    @task
    def puntuar(self):
        self.client.post("/score", json={"jugador": self.jugador, "puntos": 1}, timeout=5)


class Espectador(HttpUser):
    wait_time = constant_pacing(2)
    manifiesto = "/live/nebula/360p.m3u8"

    def on_start(self):
        self.indice = 0

    @task
    def segmento(self):
        with self.client.get(self.manifiesto, name="manifiesto", timeout=5,
                             catch_response=True) as response:
            if not response.ok:
                return
            segmentos = [
                line for line in response.text.splitlines()
                if line and not line.startswith("#") and urlsplit(line).path.endswith(".ts")
                and not urlsplit(line).netloc and not urlsplit(line).scheme
            ]
            if not segmentos:
                response.failure("Manifiesto sin segmentos TS del mismo origen")
                return
        ruta = urljoin(self.manifiesto, segmentos[self.indice % len(segmentos)])
        self.indice += 1
        with self.client.get(ruta, name="segmento", timeout=5,
                             catch_response=True) as response:
            if response.ok and response.elapsed.total_seconds() > 2:
                response.failure("Rebuffering: descarga superior a 2 s")
