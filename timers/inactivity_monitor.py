import asyncio
from datetime import datetime, timedelta, timezone
import redis.asyncio as redis

from graph.builder import build_graph
from config.settings import REDIS_URL

# Configuraciones
REMINDER_MINUTES = 5
CLOSE_MINUTES = 10
REDIS_LAST_ACTIVE_PREFIX = "thread_last_active:"
REDIS_STATUS_PREFIX = "thread_inactivity_status:"
GRAPH_NAMESPACE = "whatsapp_sessions"

redis_client = redis.from_url(REDIS_URL, decode_responses=True)

async def detect_inactive_threads_and_trigger_flow():
    now = datetime.now(timezone.utc)
    keys = await redis_client.keys(f"{REDIS_LAST_ACTIVE_PREFIX}*")

    for key in keys:
        thread_id = key.replace(REDIS_LAST_ACTIVE_PREFIX, "")
        last_active_str = await redis_client.get(key)
        if not last_active_str:
            continue

        last_active = datetime.fromisoformat(last_active_str)
        inactivity = now - last_active

        # Verificar estado actual
        status_key = f"{REDIS_STATUS_PREFIX}{thread_id}"
        current_status = await redis_client.get(status_key)

        # Acción: enviar recordatorio si pasó REMINDER_MINUTES
        if inactivity >= timedelta(minutes=REMINDER_MINUTES) and current_status != "reminder":
            print(f"[INACTIVO - RECORDATORIO] Hilo: {thread_id}")

            app = build_graph()
            await app.invoke(
                {
                    "user_input": None,
                    "timeout_detected": "reminder",
                    "thread_id": thread_id,
                },
                config={"thread_id": thread_id}
            )

            await redis_client.set(status_key, "reminder", ex=3600)

        # Acción: cerrar conversación si pasó CLOSE_MINUTES
        elif inactivity >= timedelta(minutes=CLOSE_MINUTES) and current_status != "closed":
            print(f"[INACTIVO - CIERRE] Hilo: {thread_id}")

            app = build_graph()
            await app.invoke(
                {
                    "user_input": None,
                    "timeout_detected": "closed",
                    "thread_id": thread_id,
                },
                config={"thread_id": thread_id}
            )

            await redis_client.set(status_key, "closed", ex=3600)

async def run_timer_loop(interval_seconds=60):
    while True:
        try:
            await detect_inactive_threads_and_trigger_flow()
        except Exception as e:
            print(f"[TIMER ERROR]: {e}")
        await asyncio.sleep(interval_seconds)
