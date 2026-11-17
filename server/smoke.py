"""Comprueba el contrato contra un servidor ya iniciado."""
import asyncio
import json
from contextlib import AsyncExitStack
from urllib.request import urlopen

import websockets
from websockets.exceptions import ConnectionClosed


async def main():
    async with AsyncExitStack() as stack:
        clients = [
            await stack.enter_async_context(websockets.connect("ws://127.0.0.1:7654"))
            for _ in range(10)
        ]
        async with websockets.connect("ws://127.0.0.1:7654") as extra:
            try:
                await asyncio.wait_for(extra.recv(), 3)
            except ConnectionClosed as exc:
                assert exc.code == 4000
            else:
                raise AssertionError("Se admitió al jugador número 11")
        await clients[0].send("null")
        await clients[0].send(json.dumps({"ping": "smoke"}))
        async with asyncio.timeout(3):
            while json.loads(await clients[0].recv()).get("pong") != "smoke":
                pass
        with urlopen("http://127.0.0.1:9100/metrics", timeout=3) as response:
            metrics = response.read().decode()
        assert "nebula_players_connected 10.0" in metrics
        assert "nebula_tick_seconds_count" in metrics
    with urlopen("http://127.0.0.1:9100/metrics", timeout=3) as response:
        assert "nebula_players_connected 0.0" in response.read().decode()
    print("PASS: 10 conexiones, 11 rechazada, ping tras JSON nulo y métricas CCU/tick")


if __name__ == "__main__":
    asyncio.run(main())
