"""Tabla de líderes Cloud Run + Firestore (con modo emulado opcional FIRESTORE_MOCK=1 para pruebas locales)."""
import os
import threading
from flask import Flask, request, jsonify
from google.cloud import firestore

app = Flask(__name__)

_lock = threading.Lock()
_memoria_scores = {}


class _DocMock:
    def __init__(self, doc_id, data):
        self.id = doc_id
        self._data = dict(data)

    def to_dict(self):
        return dict(self._data)


class _DocRefMock:
    def __init__(self, doc_id):
        self.id = doc_id

    def set(self, data, merge=False):
        with _lock:
            actual = _memoria_scores.get(self.id, {"puntos": 0}) if merge else {"puntos": 0}
            valor = data.get("puntos")
            if isinstance(valor, firestore.Increment):
                inc = getattr(valor, "_value", getattr(valor, "value", 0))
                actual["puntos"] = actual.get("puntos", 0) + inc
            elif isinstance(valor, int):
                actual["puntos"] = valor
            _memoria_scores[self.id] = actual


class _QueryMock:
    def __init__(self, items):
        self._items = items

    def limit(self, n):
        return _QueryMock(self._items[:n])

    def stream(self):
        return list(self._items)


class _ColeccionMock:
    def document(self, doc_id):
        return _DocRefMock(doc_id)

    def order_by(self, field, direction=firestore.Query.DESCENDING):
        reverso = direction == firestore.Query.DESCENDING
        with _lock:
            ordenados = sorted(
                (_DocMock(k, v) for k, v in _memoria_scores.items()),
                key=lambda d: d.to_dict().get(field, 0),
                reverse=reverso,
            )
        return _QueryMock(ordenados)


def coleccion():
    if os.getenv("FIRESTORE_MOCK") == "1":
        return _ColeccionMock()
    return firestore.Client().collection("scores")


@app.post("/score")
def guardar():
    datos = request.get_json(silent=True)
    if not isinstance(datos, dict):
        return jsonify(error="Se requiere un objeto JSON"), 400
    jugador = datos.get("jugador")
    puntos = datos.get("puntos")
    if (
        not isinstance(jugador, str)
        or not jugador.strip()
        or len(jugador) > 64
        or "/" in jugador
        or jugador in {".", ".."}
        or (jugador.startswith("__") and jugador.endswith("__"))
    ):
        return jsonify(error="jugador inválido"), 400
    if type(puntos) is not int or not 0 <= puntos <= 1_000_000:
        return jsonify(error="puntos debe ser entero entre 0 y 1000000"), 400
    coleccion().document(jugador).set({"puntos": firestore.Increment(puntos)}, merge=True)
    return jsonify(ok=True), 201


@app.get("/top")
def top():
    datos = coleccion().order_by("puntos", direction=firestore.Query.DESCENDING).limit(10).stream()
    return jsonify([{"jugador": doc.id, **doc.to_dict()} for doc in datos])


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
