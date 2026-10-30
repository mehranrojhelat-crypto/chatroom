import asyncio
import json
from typing import Dict, List

import redis.asyncio as aioredis
from fastapi import WebSocket

from app.config import settings


class ConnectionManager:
    """WebSocket محلی + انتشار از طریق Redis برای چند instance."""

    def __init__(self):
        self.active: Dict[str, List[WebSocket]] = {}
        self.redis: aioredis.Redis | None = None
        self.pubsub = None
        self._listener_task = None

    async def init_redis(self):
        self.redis = aioredis.from_url(settings.redis_url, decode_responses=True)
        self.pubsub = self.redis.pubsub()
        await self.pubsub.psubscribe("room:*")
        self._listener_task = asyncio.create_task(self._listen())

    async def close(self):
        if self._listener_task:
            self._listener_task.cancel()
        if self.pubsub:
            await self.pubsub.close()
        if self.redis:
            await self.redis.close()

    async def _listen(self):
        async for msg in self.pubsub.listen():
            if msg["type"] != "pmessage":
                continue
            channel = msg["channel"]  # room:ABC123
            room_code = channel.split(":", 1)[-1]
            try:
                data = json.loads(msg["data"])
            except json.JSONDecodeError:
                continue
            await self._local_broadcast(room_code, data)

    async def connect(self, websocket: WebSocket, room_code: str):
        await websocket.accept()
        self.active.setdefault(room_code, []).append(websocket)

    def disconnect(self, websocket: WebSocket, room_code: str):
        if room_code in self.active:
            if websocket in self.active[room_code]:
                self.active[room_code].remove(websocket)
            if not self.active[room_code]:
                del self.active[room_code]

    async def _local_broadcast(self, room_code: str, message: dict):
        dead = []
        for ws in self.active.get(room_code, []):
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws, room_code)

    async def publish(self, room_code: str, message: dict):
        if self.redis:
            await self.redis.publish(f"room:{room_code}", json.dumps(message))
        else:
            await self._local_broadcast(room_code, message)


manager = ConnectionManager()
