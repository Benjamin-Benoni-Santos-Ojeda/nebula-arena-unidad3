import json
import lambda_function


def test_lambda_post_y_get_top(monkeypatch):
    monkeypatch.setenv("DYNAMODB_MOCK", "1")
    lambda_function._memoria_dynamo.clear()

    ev_post_1 = {
        "requestContext": {"http": {"method": "POST", "path": "/score"}},
        "body": json.dumps({"jugador": "ana", "puntos": 1250}),
    }
    r1 = lambda_function.lambda_handler(ev_post_1)
    assert r1["statusCode"] == 201

    ev_post_2 = {
        "requestContext": {"http": {"method": "POST", "path": "/score"}},
        "body": json.dumps({"jugador": "ana", "puntos": 250}),
    }
    assert lambda_function.lambda_handler(ev_post_2)["statusCode"] == 201

    ev_post_3 = {
        "requestContext": {"http": {"method": "POST", "path": "/score"}},
        "body": json.dumps({"jugador": "benjamin", "puntos": 2000}),
    }
    assert lambda_function.lambda_handler(ev_post_3)["statusCode"] == 201

    ev_get = {"requestContext": {"http": {"method": "GET", "path": "/top"}}}
    r_top = lambda_function.lambda_handler(ev_get)
    assert r_top["statusCode"] == 200
    datos = json.loads(r_top["body"])
    assert datos == [
        {"jugador": "benjamin", "puntos": 2000},
        {"jugador": "ana", "puntos": 1500},
    ]
