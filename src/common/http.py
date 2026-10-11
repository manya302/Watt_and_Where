from __future__ import annotations

import base64
import binascii
import functools
import json
import logging
import os

from botocore.exceptions import BotoCoreError, ClientError

from .storage import MissingData


logger = logging.getLogger("wattwhere")
logger.setLevel(logging.INFO)


class APIError(Exception):
    def __init__(self, status, code, message):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


def response(status, payload):
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json; charset=utf-8",
            "Access-Control-Allow-Origin": os.environ.get(
                "FRONTEND_ORIGIN", "http://localhost:3000"
            ),
            "Access-Control-Allow-Headers": "Content-Type,X-Api-Key",
            "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
            "Vary": "Origin",
        },
        "body": json.dumps(payload, ensure_ascii=False, allow_nan=False),
    }


def validate_request(event):
    # This demo operates on one configured apartment and accepts no input fields.
    if event.get("queryStringParameters"):
        raise APIError(400, "BAD_INPUT", "Query parameters are not supported.")

    raw = event.get("body")
    if raw in (None, ""):
        return

    try:
        if event.get("isBase64Encoded"):
            raw = base64.b64decode(raw, validate=True).decode("utf-8")
        body = json.loads(raw)
    except (ValueError, TypeError, UnicodeError, binascii.Error):
        raise APIError(400, "BAD_INPUT", "Request body must be an empty JSON object.")

    if body != {}:
        raise APIError(400, "BAD_INPUT", "Request body must be an empty JSON object.")


def endpoint(function):
    @functools.wraps(function)
    def wrapped(event, context):
        request_id = getattr(context, "aws_request_id", None) or (
            event.get("requestContext") or {}
        ).get("requestId", "local")

        error_type = None
        try:
            validate_request(event)
            payload = function(event, context)
            result = response(200, payload)
        except APIError as exc:
            result = response(exc.status, {
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "request_id": request_id,
                }
            })
        except MissingData:
            result = response(404, {
                "error": {
                    "code": "NOT_FOUND",
                    "message": "Required data is missing. Load the demo data first.",
                    "request_id": request_id,
                }
            })
        except (BotoCoreError, ClientError) as exc:
            error_type = type(exc).__name__
            result = response(503, {
                "error": {
                    "code": "AWS_UNAVAILABLE",
                    "message": "An AWS dependency is unavailable. Try again later.",
                    "request_id": request_id,
                }
            })
        except Exception as exc:
            error_type = type(exc).__name__
            result = response(500, {
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "The request could not be completed.",
                    "request_id": request_id,
                }
            })

        # Do not log API keys, raw records, model prompts, or presigned URLs.
        logger.info(json.dumps({
            "event": "request_complete",
            "handler": function.__name__,
            "request_id": request_id,
            "status": result["statusCode"],
            "error_type": error_type,
        }))
        return result

    return wrapped