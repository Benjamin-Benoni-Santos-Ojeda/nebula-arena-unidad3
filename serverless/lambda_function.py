"""Tabla de líderes Serverless para AWS Lambda + DynamoDB (Práctica 3.5 - Opción AWS del PDF)."""
import base64
from decimal import Decimal
import json
import os

try:
    import boto3
except ImportError:
    boto3 = None

TABLE_NAME = os.getenv("DYNAMODB_TABLE", "nebula-scores")
REGION = os.getenv("AWS_REGION", "us-east-2")
_memoria_dynamo = {}


class _TablaMock:
    def update_item(self, Key, UpdateExpression, ExpressionAttributeValues):
        jugador = Key["jugador"]
        actual = _memoria_dynamo.get(jugador, {"jugador": jugador, "puntos": Decimal(0), "partidas": Decimal(0)})
        actual["puntos"] += ExpressionAttributeValues[":p"]
        actual["partidas"] += Decimal(ExpressionAttributeValues[":uno"])
        _memoria_dynamo[jugador] = actual

    def scan(self, ProjectionExpression=None):
        return {"Items": list(_memoria_dynamo.values())}


def obtener_tabla():
    if os.getenv("DYNAMODB_MOCK") == "1" or boto3 is None:
        return _TablaMock()
    return boto3.resource("dynamodb", region_name=REGION).Table(TABLE_NAME)


def lambda_handler(event, context=None):
    http_ctx = event.get("requestContext", {}).get("http", {})
    metodo = http_ctx.get("method") or event.get("httpMethod", "GET")
    ruta = http_ctx.get("path") or event.get("rawPath", "/")

    tabla = obtener_tabla()

    if metodo == "POST":
        body = event.get("body") or "{}"
        if event.get("isBase64Encoded"):
            body = base64.b64decode(body).decode("utf-8")
        try:
            d = json.loads(body) if isinstance(body, str) else body
        except json.JSONDecodeError:
            return {"statusCode": 400, "body": json.dumps({"error": "JSON inválido"})}

        if not isinstance(d, dict):
            return {"statusCode": 400, "body": json.dumps({"error": "Se requiere un objeto JSON"})}

        jugador = d.get("jugador")
        puntos = d.get("puntos")
        if not isinstance(jugador, str) or not jugador.strip() or len(jugador) > 64:
            return {"statusCode": 400, "body": json.dumps({"error": "jugador inválido"})}
        if type(puntos) is not int or not 0 <= puntos <= 1_000_000:
            return {"statusCode": 400, "body": json.dumps({"error": "puntos debe ser entero entre 0 y 1000000"})}

        tabla.update_item(
            Key={"jugador": jugador},
            UpdateExpression="ADD puntos :p, partidas :uno",
            ExpressionAttributeValues={":p": Decimal(puntos), ":uno": 1},
        )
        return {
            "statusCode": 201,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"ok": True, "ruta": ruta}),
        }

    items = tabla.scan(ProjectionExpression="jugador, puntos")["Items"]
    top = sorted(items, key=lambda i: i["puntos"], reverse=True)[:10]
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(
            [{"jugador": i["jugador"], "puntos": int(i["puntos"])} for i in top]
        ),
    }
