# fastapi-headless-wamp

[![PyPI](https://img.shields.io/pypi/v/fastapi-headless-wamp)](https://pypi.org/project/fastapi-headless-wamp/)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/fastapi-headless-wamp)](https://pypi.org/project/fastapi-headless-wamp/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/fastapi-headless-wamp)](https://pypi.org/project/fastapi-headless-wamp/)
[![Tests](https://github.com/KSDaemon/fastapi-headless-wamp/actions/workflows/lint-and-test.yml/badge.svg)](https://github.com/KSDaemon/fastapi-headless-wamp/actions/workflows/lint-and-test.yml)
[![License](https://img.shields.io/pypi/l/fastapi-headless-wamp)](https://github.com/KSDaemon/fastapi-headless-wamp/blob/main/LICENSE)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

![fastapi-headless-wamp logo](https://raw.githubusercontent.com/KSDaemon/fastapi-headless-wamp/main/misc/wamp-fast-api-logo.png)

Full bidirectional [WAMP](https://wamp-proto.org/) (Web Application Messaging Protocol) RPC and PubSub 
for [FastAPI](https://fastapi.tiangolo.com/) — **without a separate WAMP router**.

Each WebSocket connection gets its own isolated peer-to-peer session between the server and the client. 
There is no shared broker or dealer infrastructure. This makes the library lightweight, easy to deploy, and ideal 
for applications that need structured bidirectional communication over WebSockets.

## Features

- **Bidirectional RPC** — register server-side procedures that clients can call, *and* call client-registered 
  procedures from the server.
- **PubSub** — subscribe to topics and publish events in both directions (server-to-client and client-to-server).
- **Progressive results** — stream intermediate results from long-running RPCs.
- **Progressive call invocations** — clients can stream input chunks to the server.
- **Call cancellation** — cancel in-flight RPCs from either side.
- **Class-based services** — group related RPCs and subscriptions into service classes with a URI prefix.
- **Pluggable serialization** — JSON, CBOR and MsgPack built-in, extensible to other formats.
- **Typed** — fully typed with strict linting via ruff.
- **wampy.js compatible** — designed to work with [wampy.js](https://github.com/KSDaemon/wampy.js) and other WAMP clients.

## Architecture

```
┌──────────────┐  WebSocket  ┌───────────────────────┐
│  WAMP Client │◄───────────►│  FastAPI Application  │
│  (wampy.js)  │  wamp.2.json│                       │
└──────────────┘             │  WampHub              │
                             │  ├─ session 1 (P2P)   │
┌──────────────┐  WebSocket  │  ├─ session 2 (P2P)   │
│  WAMP Client │◄───────────►│  └─ session N (P2P)   │
└──────────────┘             └───────────────────────┘
```

Each WebSocket connection creates an **isolated peer-to-peer WAMP session**. There is no shared router — the server 
and client communicate directly within the session. This means:

- **No external WAMP router** (like Crossbar.io) is required.
- Each session is fully independent: client-registered RPCs and subscriptions are scoped to that session.
- Server-side RPCs and subscriptions (registered via decorators) are shared across all sessions.

## Installation

```bash
pip install fastapi-headless-wamp
```

With binary serialization (CBOR and/or MsgPack):

```bash
pip install fastapi-headless-wamp[cbor]
pip install fastapi-headless-wamp[msgpack]
```

## Quick Start

### Standalone Decorators

```python
from fastapi import FastAPI
from fastapi_headless_wamp import WampHub, WampSession

app = FastAPI()
wamp = WampHub(realm="realm1")


# Register a server-side RPC
@wamp.register("com.example.add")
async def add(session: WampSession, a: int, b: int) -> int:
    return a + b


# Mount the WAMP WebSocket endpoint
app.include_router(wamp.get_router(path="/ws"))
```

Run with `uvicorn`:

```bash
uvicorn myapp:app --host 0.0.0.0 --port 8000
```

Clients connect via WebSocket to `ws://localhost:8000/ws` using the `wamp.2.json` subprotocol and 
can call `com.example.add`.

### Class-Based Services

```python
from fastapi import FastAPI
from fastapi_headless_wamp import WampHub, WampService, WampSession, rpc

app = FastAPI()
wamp = WampHub(realm="realm1")


class MathService(WampService):
    prefix = "com.example.math"

    @rpc()
    async def add(self, session: WampSession, *, a: int, b: int) -> int:
        return a + b

    @rpc("multiply")
    async def mul(self, session: WampSession, *, a: int, b: int) -> int:
        return a * b


wamp.register_service(MathService())
app.include_router(wamp.get_router(path="/ws"))
```

Clients can now call `com.example.math.add` and `com.example.math.multiply`.

### Manual WebSocket Handler

If you need more control, use `handle_websocket` directly:

```python
from fastapi import FastAPI, WebSocket
from fastapi_headless_wamp import WampHub, WampSession

app = FastAPI()
wamp = WampHub(realm="realm1")


@wamp.register("com.example.greet")
async def greet(session: WampSession, name: str) -> str:
    return f"Hello, {name}!"


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await wamp.handle_websocket(websocket)
```

## Bidirectional RPC

The server can call RPCs that clients have registered on their session:

```python
from fastapi_headless_wamp import WampHub, WampSession

wamp = WampHub(realm="realm1")


@wamp.on_session_open
async def on_open(session: WampSession) -> None:
    # Call a client-registered procedure
    result = await session.call("com.client.get_status")
    print(f"Client status: {result}")
```

## PubSub

### Server publishes to clients

```python
@wamp.on_session_open
async def on_open(session: WampSession) -> None:
    # Publish to this specific session (if subscribed)
    await session.publish("com.example.news", args=["breaking update"])

    # Publish to all connected sessions that are subscribed
    await wamp.publish_to_all("com.example.news", args=["broadcast"])
```

### Server handles client publishes

```python
@wamp.subscribe("com.example.chat")
async def on_chat(session: WampSession, *args, **kwargs) -> None:
    message = args[0] if args else kwargs.get("message", "")
    print(f"Chat from session {session.session_id}: {message}")
```

## Progressive Results

Server RPC handlers can stream intermediate results:

```python
from typing import Any
from collections.abc import Awaitable, Callable


@wamp.register("com.example.long_task")
async def long_task(
    session: WampSession,
    n: int,
    _progress: Callable[[Any], Awaitable[None]] | None = None,
) -> str:
    for i in range(n):
        if _progress is not None:
            await _progress(f"Step {i + 1}/{n}")
    return "done"
```

The client receives each progressive result as it is produced, then the final result.

## Call Cancellation

Clients can cancel in-flight RPCs. The server supports three cancel modes:

- `kill` (default) — cancel the handler's asyncio task.
- `skip` — stop waiting for the result, let the handler keep running.
- `killnowait` — cancel the task and respond immediately.

The server can also cancel calls to clients:

```python
@wamp.on_session_open
async def on_open(session: WampSession) -> None:
    # Start a call, then cancel it
    import asyncio

    task = asyncio.create_task(session.call("com.client.slow_op"))
    await asyncio.sleep(1)
    await session.cancel(1)  # cancel by request ID
```

## Session Lifecycle Callbacks

```python
@wamp.on_session_open
async def on_open(session: WampSession) -> None:
    print(f"Session {session.session_id} connected")


@wamp.on_session_close
async def on_close(session: WampSession) -> None:
    print(f"Session {session.session_id} disconnected")
```

## Serialization

### Built-in serializers

| Serializer | Subprotocol | Format | Install |
|---|---|---|---|
| `JsonSerializer` | `wamp.2.json` | Text (UTF-8) | included |
| `CborSerializer` | `wamp.2.cbor` | Binary | `pip install fastapi-headless-wamp[cbor]` |
| `MsgpackSerializer` | `wamp.2.msgpack` | Binary | `pip install fastapi-headless-wamp[msgpack]` |

All are registered automatically at import time (CBOR only when `cbor2` is installed, MsgPack only when
`msgpack` is installed).
The server advertises all available subprotocols during the WebSocket handshake and the
client picks one.

All serializers handle **Pydantic models**, **dataclasses**, `datetime`, `Decimal`, `UUID`,
`set`/`frozenset`, and `bytes` out of the box — RPC handlers can return these types directly
without manual serialization.

CBOR preserves native types (e.g. `datetime` stays a datetime, not a string), while JSON and MsgPack
convert them to string representations. MsgPack and CBOR both carry `bytes` natively.

### Custom serializers

To add another serializer (e.g. UBJSON), implement the `Serializer` protocol:

```python
from fastapi_headless_wamp import Serializer, register_serializer


class UbjsonSerializer:
    @property
    def protocol(self) -> str:
        return "ubjson"

    @property
    def is_binary(self) -> bool:
        return True

    def encode(self, data: list) -> bytes:
        import ubjson

        return ubjson.dumpb(data)

    def decode(self, data: str | bytes) -> list:
        import ubjson

        return ubjson.loadb(data)


register_serializer(UbjsonSerializer())
```

Clients can then connect with the `wamp.2.ubjson` subprotocol.

## Migrating to a full-fledged WAMP router

This library lets a project speak WAMP from day one without running a router. When the project grows and needs real 
routing, you can put a full-fledged WAMP router (e.g. [Crossbar.io](https://crossbar.io)) in place. The backend then 
connects to the router as a regular WAMP client, and the clients keep speaking plain WAMP. Most of the work is on the 
backend side, but a few behaviors differ behind a router. Designing for them from the start keeps the switch painless.

### Client-registered procedures

Here, procedures registered by a client are scoped to its session, so every client can register the *same* URI 
(e.g. `com.client.get_status`) and the server calls each one through `session.call()`.

Behind a router, procedure URIs are global within a realm. The second client registering the same URI gets 
`wamp.error.procedure_already_exists`, and a caller can no longer pick which client to invoke.

Workarounds:

- **Per-client URIs** — include something unique to the client in the URI, e.g. its session ID or a user/device ID: 
  `com.client.<session_id>.get_status`. This works the same way with this library and behind a router, so it is the 
  safest choice from the start.
- **Shared registrations** — if any client may answer the call, register with an invocation policy 
  (`roundrobin`, `random`, ...) so the router allows several registrations of one URI. This only fits when it does not 
  matter which client handles the call.

### Client-to-client PubSub

Here, a client's publish reaches only the server's subscription handlers; other clients never receive it, even if 
they are subscribed to the same topic.

Behind a router, events are delivered to every subscriber of the topic, including other clients. An app that relies on 
client publishes being private to the server will suddenly start receiving its peers' events.

Workarounds:

- Use separate topics for client-to-server messages (e.g. `com.app.client.chat`) and server-to-client events 
  (e.g. `com.app.chat`), so clients never subscribe to topics other clients publish to.
- Or restrict delivery explicitly with `eligible` / `exclude` publish options, or with router-side authorization rules.

### Server side

This is where most of the migration work is. With this library, the FastAPI app terminates WAMP sessions itself and 
its RPC handlers and subscriptions are wired in via `@wamp.register` / `@wamp.subscribe` or `WampService` classes. 
Behind a router, the backend no longer accepts WAMP connections; instead, the RPC handlers and subscriptions move into 
separate WAMP client components that connect to the router and register / subscribe there like any other peer.

For Python backends, use a WAMP client library such as 
[Autobahn|Python](https://github.com/crossbario/autobahn-python) or 
[xconn-python](https://github.com/xconnio/xconn-python), together with a router of your choice 
(e.g. [Crossbar.io](https://crossbar.io) or [Nexus](https://github.com/gammazero/nexus)). Keeping your handlers as plain async functions with the business logic 
separate from the WAMP wiring makes this step mostly mechanical: only the registration code changes.

A few more things to map:

- The `session` argument of server-side handlers is gone. If a handler needs to know the calling client, enable 
  caller/publisher disclosure (`disclose_me`) and read the caller's session ID from the invocation/event details.
- Calls from the server to a specific client use that client's own URI (see above).
- Publishing to a single session (`session.publish`) maps to a publish with `eligible=[session_id]`, and 
  `hub.publish_to_all` becomes a regular publish.
- Session lifecycle callbacks (`on_session_open` / `on_session_close`) map to the router's meta-events 
  (`wamp.session.on_join` / `wamp.session.on_leave`).

## Clients Compatibility

This library is designed to be compatible with [wampy.js](https://github.com/KSDaemon/wampy.js) and other standard WAMP clients. The server 
advertises the following WAMP role features:

**Dealer features:**
- `progressive_call_results`
- `call_canceling`
- `caller_identification`
- `call_timeout`

**Broker features:**
- `publisher_identification`
- `publisher_exclusion`
- `subscriber_blackwhite_listing`

## API Reference

### `WampHub(realm="realm1")`

The central hub that manages WAMP sessions. Key methods and decorators:

| Method / Decorator               | Description                                         |
|----------------------------------|-----------------------------------------------------|
| `@hub.register(uri)`             | Register a server-side RPC handler                  |
| `@hub.subscribe(topic)`          | Register a server-side subscription handler         |
| `hub.register_service(service)`  | Register a `WampService` instance                   |
| `@hub.on_session_open`           | Callback when a session completes handshake         |
| `@hub.on_session_close`          | Callback when a session disconnects                 |
| `hub.handle_websocket(ws)`       | Full async WebSocket handler                        |
| `hub.get_router(path="/ws")`     | Get a FastAPI `APIRouter` with the WAMP endpoint    |
| `hub.publish_to_all(topic, ...)` | Publish an event to all subscribed sessions         |
| `hub.sessions`                   | Dict of active sessions (session_id -> WampSession) |
| `hub.session_count`              | Number of active sessions                           |

### `WampSession`

Represents a single WAMP session. Key methods:

| Method                                     | Description                       |
|--------------------------------------------|-----------------------------------|
| `session.call(uri, args, kwargs, timeout)` | Call a client-registered RPC      |
| `session.cancel(request_id, mode)`         | Cancel a pending call to a client |
| `session.publish(topic, args, kwargs)`     | Publish an event to this client   |

### `WampService`

Base class for grouping RPCs with a URI prefix. Use `@rpc()` and `@subscribe()` to mark methods.

### Error Classes

| Exception                    | WAMP Error URI                        |
|------------------------------|---------------------------------------|
| `WampError`                  | (base class)                          |
| `WampNoSuchProcedure`        | `wamp.error.no_such_procedure`        |
| `WampNoSuchSubscription`     | `wamp.error.no_such_subscription`     |
| `WampRuntimeError`           | `wamp.error.runtime_error`            |
| `WampCallTimeout`            | `wamp.error.canceled`                 |
| `WampCanceled`               | `wamp.error.canceled`                 |
| `WampProcedureAlreadyExists` | `wamp.error.procedure_already_exists` |
| `WampProtocolError`          | (protocol-level error)                |
| `WampInvalidMessage`         | (message validation error)            |

## License

Apache 2.0 — see [LICENSE](LICENSE) for details.
