import main


def test_post_score_y_get_top_acumulativo(monkeypatch):
    monkeypatch.setenv("FIRESTORE_MOCK", "1")
    main._memoria_scores.clear()
    client = main.app.test_client()

    # Acumulación atómica por jugador
    r1 = client.post("/score", json={"jugador": "ana", "puntos": 1250})
    assert r1.status_code == 201
    r2 = client.post("/score", json={"jugador": "ana", "puntos": 250})
    assert r2.status_code == 201
    r3 = client.post("/score", json={"jugador": "luis", "puntos": 1800})
    assert r3.status_code == 201

    top = client.get("/top")
    assert top.status_code == 200
    datos = top.get_json()
    assert datos == [
        {"jugador": "luis", "puntos": 1800},
        {"jugador": "ana", "puntos": 1500},
    ]


def test_validacion_entradas_invalidas(monkeypatch):
    monkeypatch.setenv("FIRESTORE_MOCK", "1")
    main._memoria_scores.clear()
    client = main.app.test_client()

    assert client.post("/score", data="no-json").status_code == 400
    assert client.post("/score", json={"jugador": "", "puntos": 10}).status_code == 400
    assert client.post("/score", json={"jugador": "../etc", "puntos": 10}).status_code == 400
    assert client.post("/score", json={"jugador": "__reservado__", "puntos": 10}).status_code == 400
    assert client.post("/score", json={"jugador": "ana", "puntos": -5}).status_code == 400
    assert client.post("/score", json={"jugador": "ana", "puntos": True}).status_code == 400
    assert client.post("/score", json={"jugador": "ana", "puntos": 2_000_000}).status_code == 400


def test_top_limita_a_10(monkeypatch):
    monkeypatch.setenv("FIRESTORE_MOCK", "1")
    main._memoria_scores.clear()
    client = main.app.test_client()

    for i in range(15):
        res = client.post("/score", json={"jugador": f"jug_{i:02d}", "puntos": i * 100})
        assert res.status_code == 201

    datos = client.get("/top").get_json()
    assert len(datos) == 10
    assert datos[0]["jugador"] == "jug_14"
    assert datos[0]["puntos"] == 1400
    assert datos[-1]["jugador"] == "jug_05"
