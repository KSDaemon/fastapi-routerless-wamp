"""fastapi-routerless-wamp: Bidirectional WAMP RPC and PubSub for FastAPI."""

import logging

from fastapi_routerless_wamp._version import __version__, __version_tuple__
from fastapi_routerless_wamp.errors import (
    WampCallTimeoutError,
    WampCanceledError,
    WampError,
    WampInvalidMessageError,
    WampNoSuchProcedureError,
    WampNoSuchSubscriptionError,
    WampProcedureAlreadyExistsError,
    WampProtocolError,
    WampRuntimeError,
)
from fastapi_routerless_wamp.hub import WampHub
from fastapi_routerless_wamp.serializers import (
    CborSerializer,
    JsonSerializer,
    MsgpackSerializer,
    Serializer,
    get_available_subprotocols,
    get_serializer,
    register_serializer,
)
from fastapi_routerless_wamp.service import WampService, rpc, subscribe
from fastapi_routerless_wamp.session import ProgressiveCallInput, WampSession

# Configure logging with NullHandler to prevent "No handler found" warnings
logging.getLogger("fastapi_routerless_wamp").addHandler(logging.NullHandler())

__all__ = [
    "CborSerializer",
    "JsonSerializer",
    "MsgpackSerializer",
    "ProgressiveCallInput",
    "Serializer",
    "WampCallTimeoutError",
    "WampCanceledError",
    "WampError",
    "WampHub",
    "WampInvalidMessageError",
    "WampNoSuchProcedureError",
    "WampNoSuchSubscriptionError",
    "WampProcedureAlreadyExistsError",
    "WampProtocolError",
    "WampRuntimeError",
    "WampService",
    "WampSession",
    "__version__",
    "__version_tuple__",
    "get_available_subprotocols",
    "get_serializer",
    "register_serializer",
    "rpc",
    "subscribe",
]
