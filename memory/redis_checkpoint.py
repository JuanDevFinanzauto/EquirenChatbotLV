from typing import Optional, Any, Dict
import json
import redis.asyncio as redis
from config.settings import REDIS_URL

class RedisCheckpoint:
    """
    Implementación personalizada de checkpoint para LangGraph usando Redis.
    Compatible con langgraph v0.4.2.
    """
    
    def __init__(self, redis_client: redis.Redis, namespace: str = "default", ttl: Optional[int] = None):
        """
        Inicializa el checkpoint de Redis.
        
        Args:
            redis_client: Cliente Redis asíncrono
            namespace: Espacio de nombres para aislar flujos
            ttl: Tiempo de vida en segundos para cada checkpoint (opcional)
        """
        self.redis = redis_client
        self.namespace = namespace
        self.ttl = ttl

    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Recupera el estado guardado para una key específica"""
        full_key = f"{self.namespace}:{key}"
        value = await self.redis.get(full_key)
        if value:
            return json.loads(value)
        return None

    async def put(self, key: str, state: Dict[str, Any]) -> None:
        """Guarda el estado para una key específica"""
        full_key = f"{self.namespace}:{key}"
        if self.ttl:
            await self.redis.setex(full_key, self.ttl, json.dumps(state))
        else:
            await self.redis.set(full_key, json.dumps(state))

    async def delete(self, key: str) -> None:
        """Elimina el estado para una key específica"""
        full_key = f"{self.namespace}:{key}"
        await self.redis.delete(full_key)

async def create_redis_checkpointer(namespace: str = "whatsapp_sessions", ttl: int = 86400) -> RedisCheckpoint:
    """
    Crea un checkpoint para LangGraph usando Redis.

    Args:
        namespace (str): Espacio de nombres para aislar flujos.
        ttl (int): Tiempo de vida en segundos para cada checkpoint (opcional).

    Returns:
        RedisCheckpoint: Instancia para usar en LangGraph.
    """
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    return RedisCheckpoint(
        redis_client=redis_client,
        namespace=namespace,
        ttl=ttl
    )

def get_redis_checkpointer(namespace: str = "whatsapp_sessions", ttl: int = 86400) -> RedisCheckpoint:
    """
    Versión sincrónica para crear el checkpoint.
    """
    import asyncio
    return asyncio.run(create_redis_checkpointer(namespace, ttl))
