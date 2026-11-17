import asyncio
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import threading
import websockets
from websockets.exceptions import ConnectionClosed

import server


def test_snapshot_incluye_jugadores():
    server.estado.clear()
    server.estado["ana"] = {"id": "ana", "x": 1.0, "y": 2.0}
    assert json.loads(server.snapshot())["e"]["ana"]["x"] == 1.0
    server.estado.clear()


def test_partida_5_vs_5():
    assert server.MAX_JUGADORES == 10


def test_tick_20_hz():
    assert server.TICK_S == 0.05


def test_ciclo_agones_ready_health_shutdown(monkeypatch):
    """Verifica que el servidor invoque /health, /ready y /shutdown según el SDK de Agones."""
    llamadas = []

    class MockAgonesHandler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            if length:
                self.rfile.read(length)
            llamadas.append(self.path)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"{}")

        def log_message(self, format, *args):
            return

    httpd = HTTPServer(("127.0.0.1", 0), MockAgonesHandler)
    port = httpd.server_port
    hilo = threading.Thread(target=httpd.serve_forever, daemon=True)
    hilo.start()

    try:
        monkeypatch.setattr(server, "SDK_PORT", str(port))
        server.conexiones.clear()
        server.estado.clear()
        server.partida["iniciada"] = False

        async def escenario():
            tarea = asyncio.create_task(server.ciclo_agones())
            await asyncio.sleep(0.15)
            assert "/health" in llamadas
            assert "/ready" in llamadas
            assert "/shutdown" not in llamadas
            # Simula inicio y fin de partida (todos los jugadores se desconectan)
            server.partida["iniciada"] = True
            await asyncio.wait_for(tarea, timeout=2.5)
            assert "/shutdown" in llamadas

        asyncio.run(escenario())
    finally:
        httpd.shutdown()
        httpd.server_close()
        server.partida["iniciada"] = False


def test_websocket_cupo_ping_y_limpieza():
    """Verifica límite de 10 jugadores, rechazo 4000 al 11º, ping/pong y limpieza de estado."""
    server.conexiones.clear()
    server.estado.clear()
    server.partida["iniciada"] = False

    async def escenario():
        async with websockets.serve(server.jugador, "127.0.0.1", 0) as ws_server:
            port = ws_server.sockets[0].getsockname()[1]
            url = f"ws://127.0.0.1:{port}"
            clientes = [await websockets.connect(url) for _ in range(10)]
            try:
                assert len(server.conexiones) == 10
                # El jugador 11 debe ser rechazado con código 4000
                async with websockets.connect(url) as extra:
                    try:
                        await asyncio.wait_for(extra.recv(), timeout=2)
                    except ConnectionClosed as exc:
                        assert exc.code == 4000
                    else:
                        raise AssertionError("No se rechazó al jugador 11")

                # Envío de posición y ping
                await clientes[0].send(json.dumps({"id": "jug1", "x": 5.0, "y": 9.0}))
                await clientes[0].send(json.dumps({"ping": 999}))
                respuesta = json.loads(await asyncio.wait_for(clientes[0].recv(), timeout=2))
                assert respuesta == {"pong": 999}
                assert server.estado["jug1"]["x"] == 5.0
            finally:
                for c in clientes:
                    await c.close()
            await asyncio.sleep(0.05)
            assert len(server.conexiones) == 0
            assert "jug1" not in server.estado

    asyncio.run(escenario())
