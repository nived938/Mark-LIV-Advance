"""JARVIS local mobile companion gateway.

Protocol is deliberately small and explicit:
hello -> pair_approved/authenticated -> execute/result.
The Android companion can therefore use WebSockets without sharing the web
dashboard's browser-session protocol.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import secrets
import time
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "memory" / "mobile_devices.json"
HOST = "0.0.0.0"
PORT = 8765


class MobileGateway:
    def __init__(self):
        self._server = None
        self._loop = None
        self._pair_codes = {}
        self._devices = self._load()
        self._connections = {}
        self._pending = {}

    @staticmethod
    def _hash(value: str) -> str:
        return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()

    def _load(self):
        try:
            data = json.loads(STATE.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _save(self):
        STATE.parent.mkdir(parents=True, exist_ok=True)
        STATE.write_text(
            json.dumps(self._devices, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def new_pairing_code(self) -> str:
        code = f"{secrets.randbelow(1_000_000):06d}"
        self._pair_codes[code] = time.time() + 600
        return code

    def list_devices(self) -> list[dict]:
        now = time.time()
        result = []
        for device_id, item in self._devices.items():
            result.append({
                "device_id": device_id,
                "name": item.get("name", "Android"),
                "model": item.get("model", ""),
                "paired_at": item.get("paired_at", 0),
                "connected": device_id in self._connections,
                "last_seen": item.get("last_seen", now),
            })
        return result

    async def _send(self, websocket, payload: dict):
        await websocket.send(json.dumps(payload, ensure_ascii=False))

    async def _handle(self, websocket):
        device_id = None
        try:
            raw = await asyncio.wait_for(websocket.recv(), timeout=15)
            hello = json.loads(raw)
            if not isinstance(hello, dict) or hello.get("type") != "hello":
                await self._send(websocket, {"type": "error", "error": "hello required"})
                return

            device = hello.get("device") or {}
            supplied_token = str(hello.get("token") or "").strip()
            pairing_code = str(hello.get("pairing_code") or "").strip()
            requested_id = str(device.get("id") or "").strip()

            if supplied_token:
                token_hash = self._hash(supplied_token)
                matches = [
                    (did, item)
                    for did, item in self._devices.items()
                    if item.get("token_hash") == token_hash
                ]
                if not matches:
                    await self._send(websocket, {"type": "error", "error": "authentication failed"})
                    return
                device_id, item = matches[0]
            else:
                expiry = self._pair_codes.get(pairing_code, 0)
                if not pairing_code or expiry <= time.time():
                    await self._send(websocket, {"type": "error", "error": "invalid or expired pairing code"})
                    return

                device_id = requested_id or uuid.uuid4().hex[:12]
                token = secrets.token_urlsafe(32)
                item = {
                    "name": str(device.get("name") or "Android"),
                    "model": str(device.get("model") or ""),
                    "token_hash": self._hash(token),
                    "paired_at": time.time(),
                    "last_seen": time.time(),
                }
                self._devices[device_id] = item
                self._save()
                self._pair_codes.pop(pairing_code, None)

                await self._send(
                    websocket,
                    {
                        "type": "pair_approved",
                        "device_id": device_id,
                        "token": token,
                        "server": {"name": "JARVIS", "protocol": 1},
                    },
                )

            item["last_seen"] = time.time()
            self._connections[device_id] = websocket
            self._save()
            await self._send(websocket, {"type": "authenticated", "device_id": device_id})

            async for raw in websocket:
                try:
                    msg = json.loads(raw)
                    if not isinstance(msg, dict):
                        continue
                    msg_type = msg.get("type")
                    if msg_type == "result":
                        request_id = str(msg.get("id") or "")
                        future = self._pending.pop(request_id, None)
                        if future and not future.done():
                            future.set_result(msg)
                    elif msg_type == "ping":
                        await self._send(websocket, {"type": "pong", "ts": time.time()})
                    item["last_seen"] = time.time()
                except Exception:
                    continue
        except asyncio.TimeoutError:
            pass
        except Exception as exc:
            print(f"[MobileGateway] Connection error: {exc}")
        finally:
            if device_id and self._connections.get(device_id) is websocket:
                self._connections.pop(device_id, None)

    async def start(self):
        if self._server is not None:
            return
        try:
            import websockets
        except ImportError:
            print("[MobileGateway] websockets is not installed.")
            return
        self._loop = asyncio.get_running_loop()
        self._server = await websockets.serve(
            self._handle,
            HOST,
            PORT,
            ping_interval=20,
            ping_timeout=20,
            max_size=4 * 1024 * 1024,
        )
        print(f"[MobileGateway] WebSocket gateway listening on {PORT}.")

        try:
            from zeroconf import ServiceInfo, Zeroconf
            self._zeroconf = Zeroconf()
            self._service_info = ServiceInfo(
                "_jarvis._tcp.local.",
                "JARVIS._jarvis._tcp.local.",
                addresses=[],
                port=PORT,
                properties={
                    b"name": b"JARVIS",
                    b"protocol": b"1",
                },
                server="jarvis.local.",
            )
            import socket
            local_ip = socket.gethostbyname(socket.gethostname())
            import ipaddress
            self._service_info = ServiceInfo(
                "_jarvis._tcp.local.",
                "JARVIS._jarvis._tcp.local.",
                addresses=[ipaddress.ip_address(local_ip).packed],
                port=PORT,
                properties={b"name": b"JARVIS", b"protocol": b"1"},
                server="jarvis.local.",
            )
            self._zeroconf.register_service(self._service_info)
            print("[MobileGateway] mDNS discovery advertised as _jarvis._tcp.")
        except Exception as exc:
            self._zeroconf = None
            print(f"[MobileGateway] mDNS discovery unavailable: {exc}")

    async def stop(self):
        if self._zeroconf is not None and getattr(self, "_service_info", None):
            try:
                self._zeroconf.unregister_service(self._service_info)
                self._zeroconf.close()
            except Exception:
                pass
            self._zeroconf = None
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

    async def command(self, device_id: str, action: str, payload: dict | None = None, timeout: float = 20):
        websocket = self._connections.get(str(device_id))
        if websocket is None:
            return {"ok": False, "result": "Android device is not connected."}

        request_id = uuid.uuid4().hex
        future = self._loop.create_future()
        self._pending[request_id] = future
        try:
            await self._send(
                websocket,
                {
                    "type": "execute",
                    "id": request_id,
                    "action": str(action),
                    "payload": payload or {},
                },
            )
            return await asyncio.wait_for(future, timeout=timeout)
        except Exception as exc:
            self._pending.pop(request_id, None)
            return {"ok": False, "result": str(exc)}
        finally:
            self._pending.pop(request_id, None)


GATEWAY = MobileGateway()
