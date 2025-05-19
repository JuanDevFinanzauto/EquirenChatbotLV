from fastapi import FastAPI, Request, Response, HTTPException, Form, BackgroundTasks
from fastapi.responses import JSONResponse
from twilio.rest import Client
import os
import pandas as pd
from dotenv import load_dotenv
import json
from datetime import datetime
import threading
import time
import uuid
from graph.builder import compile, main
import sqlite3
from msgpack import ExtType
import msgpack
from contextlib import closing
from pathlib import Path
import requests
from requests.auth import HTTPBasicAuth
from urllib.parse import urlparse
import ast
from langchain_core.messages import HumanMessage
import uvicorn
from sqlalchemy import create_engine, text
import urllib.parse

graph = compile()

# Configuración inicial
load_dotenv()
app = FastAPI(title="Twilio WhatsApp Integration")

driver = os.getenv('driver')
username = os.getenv('username')
password = os.getenv('password')
host = os.getenv('host')
database = os.getenv('database')
schema = os.getenv('schema')

params = urllib.parse.quote_plus(
    f'DRIVER={driver};SERVER={host};DATABASE={database};UID={username};PWD={password}'
)

engine = create_engine(f'mssql+pyodbc:///?odbc_connect={params}&defaultSchema={schema}')

print(f"Conectando a SQL Server en {params}")
print("Conexión exitosa a SQL Server")

# Configuración Twilio
account_sid = os.getenv('TWILIO_ACCOUNT_SID')
auth_token = os.getenv('TWILIO_AUTH_TOKEN')
client = Client(account_sid, auth_token)

TWILIO_WHATSAPP_NUMBER = ('whatsapp:+573132457578')
# Multiagente API
MULTIAGENTE_BASE_URL = os.getenv("ENDPOINT_MULTIAGENTE", "http://192.168.40.18:8071/api/v1")

# Base de datos

script_directory = Path(__file__).resolve().parent
db_path = str(script_directory)+'/checkpoints.db'
# Caches y timers separados

cache_cobranza = {}
cache_sac = {}
user_timers_cobranza = {}
user_timers_sac = {}

def pretty_print_json(json_data, indent=2, sort_keys=False):
    """
    Pretty prints JSON data with proper formatting.

    Args:
        json_data: JSON data as string or Python dict/list
        indent: Number of spaces for indentation (default: 2)
        sort_keys: Whether to sort dictionary keys (default: False)
    """
    # If input is a string, try to parse it as JSON
    if isinstance(json_data, str):
        try:
            json_data = json.loads(json_data)
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON: {e}")
            return

    # Pretty print the JSON
    try:
        formatted_json = json.dumps(
            json_data, indent=indent, sort_keys=sort_keys, ensure_ascii=False)
        print(formatted_json)
    except Exception as e:
        print(f"Error formatting JSON: {e}")


def recursive_deserialize(data):
    # Check if data is MessagePack serialized
    if isinstance(data, (bytes, bytearray)):
        try:
            data = msgpack.unpackb(data, ext_hook=ext_type_handler)
        except Exception:
            return data  # Return original data if deserialization fails
    
    # Recursively process dictionaries
    if isinstance(data, dict):
        return {key: recursive_deserialize(value) for key, value in data.items()}
    
    # Recursively process lists
    if isinstance(data, list):
        return [recursive_deserialize(item) for item in data]
    
    return data  # Return primitive types as is

# Custom handler for msgpack.ExtType
def ext_type_handler(code, data):
    if code == 5:  # Assuming 'code=5' represents a serialized custom object
        try:
            # Attempt to decode nested MessagePack or transform data
            return msgpack.unpackb(data)  # Adjust logic here as needed
        except Exception:
            print(f"Unrecognized ExtType(code={code}, data={data}")
            return f"Unrecognized ExtType(code={code}, data={data})"
    # Return the ExtType object as is if not handled
    print('devuelto tal cual')
    return ExtType(code, data)

# Function to process an entire DataFrame
def deserialize_dataframe(df):
    return df.map(recursive_deserialize)


def obtener_archivo(media_url, twilio_account_sid, twilio_auth_token):
    # Verificar si el directorio 'archivos' existe, si no, crearlo
    if not os.path.exists("archivos"):
        os.makedirs("archivos")
    
    # Hacer la solicitud GET para obtener el archivo
    response = requests.get(media_url, auth=HTTPBasicAuth(twilio_account_sid, twilio_auth_token))
    
    if response.status_code == 200:
        print(response.url)
        
        return response.url  # Devuelve la ruta del archivo guardado
    else:
        print(f"Error al obtener el archivo: {response.status_code}")
        return None
    
# Función para transferir al multiagente
def transfer_to_multiagent(from_number, message, thread_id):
    """
    Envía la conversación al multiagente para que un asesor continúe la interacción.
    Cambia el endpoint a multiagente y redirige todos los mensajes.
    """

    stop_inactivity_timer(thread_id)
    print(f"[Transferencia al Multiagente] Notificación enviada a {from_number}.")

    try:
        payload = {
            "thread_id": thread_id,
            "from_number": from_number,
            "message": message,
        }

        response = requests.post(f"{MULTIAGENTE_BASE_URL}/chatbot/webhook", json=payload)
        response.raise_for_status()

        print(f"[Transferencia al Multiagente] Transferencia exitosa. Cambiando el endpoint a Multiagente para {from_number}.")

        cache_sac[from_number] = "multiagente"
        return response.json()
    
    except requests.exceptions.RequestException as e:
        print(f"[Transferencia al Multiagente] Error: {e}")
        return {"success": False, "error": str(e)}
    except Exception as e:
        print(f"[Transferencia al Multiagente] Error: {e}")
        return {"success": False, "error": str(e)}

def update_graph_states(thread_id, states):
    """
    Actualiza los estados del grafo antes de procesar la lógica principal.

    Args:
        thread_id (str): El ID del hilo asociado al grafo.
        states (dict): Los nuevos estados a actualizar.
    """
    config = {"configurable": {"thread_id": thread_id}}
    graph.update_state(config, states)
    print(f"[Graph] Estados actualizados: {states} para thread_id: {thread_id}")


def limit_message_length(message, max_length=1590):
    """
    Limita la longitud de un mensaje a un número máximo de caracteres.
    Si el mensaje excede el límite, lo corta y agrega un indicador de truncado.
    """
    if len(message) > max_length:
        return message[:max_length] + "..."
    return message

# --- Clase personalizada para manejo robusto de temporizadores ---
class InactivityTimer(threading.Thread):
    def __init__(self, user_id, callback, termination_callback):
        super().__init__(daemon=True)
        self.user_id = user_id
        self.callback = callback
        self.termination_callback = termination_callback
        self.event = threading.Event()
        self.last_activity = time.time()
        self.start_time = time.time()
        self.notification_sent = False

    def run(self):
        while not self.event.is_set():
            current_time = time.time()
            elapsed = current_time - self.last_activity
            total_elapsed = current_time - self.start_time

            # Notificación a los 5 minutos de inactividad
            if elapsed >= 300 and not self.notification_sent:  # 300 seg = 5 min
                self.callback(self.user_id)
                self.notification_sent = True

            # Finalización a los 10 minutos totales
            if total_elapsed >= 600:  # 600 seg = 10 min
                self.termination_callback(self.user_id)
                self.stop()
                break

            time.sleep(1)  # Verificación cada segundo

    def reset(self):
        """Reinicia el contador de inactividad"""
        self.last_activity = time.time()
        self.notification_sent = False

    def stop(self):
        """Detiene el temporizador definitivamente"""
        self.event.set()

# --- Módulo de gestión de temporizadores ---
active_timers = {}

def callback(user_id):
    print(user_id)
    response_message = "¡Hola! 😊 Solo quería confirmar si sigues por aquí. ¿En que te puedo ayudar?"
    client.messages.create(
        body=response_message,
        from_=TWILIO_WHATSAPP_NUMBER,
        to=user_id
    )
    print(f"[EQUIRENT] Recordatorio enviado a {user_id}")

def max_time_reached_callback(user_id):
    print(user_id)
    config = {"configurable": {"thread_id": user_id}}
    graph.update_state(config, {"the_end": True, "telephone": user_id[:22]})
    
    response_message = "El chat ha llegado a su fin por ahora. ¡Muchas gracias por tu tiempo! 😊"
    client.messages.create(
        body=response_message,
        from_=TWILIO_WHATSAPP_NUMBER,
        to=user_id
    )
    print(f"[EQUIRENT] Conversación finalizada para {user_id}")


def start_inactivity_timer(user_id):
    """Inicia o reinicia el temporizador para un usuario"""
    # Detener temporizador existente si hay uno
    if user_id  in active_timers:
        active_timers[user_id ].stop()
    
    # Crear nuevo temporizador
    timer = InactivityTimer(
        user_id=user_id ,
        callback=callback,
        termination_callback=max_time_reached_callback
    )
    active_timers[user_id ] = timer
    timer.start()

def stop_inactivity_timer(user_id ):
    """Detiene el temporizador de un usuario"""
    print(user_id)
    print("Antes: ",active_timers.keys())
    if user_id in active_timers:
        active_timers[user_id].stop()
        active_timers[user_id].join()
        del active_timers[user_id]
    print("Despues", active_timers.keys())

def auto_manage_timer(thread_id, the_end, human, encuesta):
    """
    Maneja los temporizadores según el estado de la conversación
    """
    if the_end or human or encuesta:
        stop_inactivity_timer(thread_id)
        print(f"[Timer] Detenido por estado: the_end={the_end}, human={human}, encuesta={encuesta}")
    else:
        stop_inactivity_timer(thread_id)
        start_inactivity_timer(thread_id)

def create_telephone_uuid(telephone):
    uuido = str(uuid.uuid4())
    return str(telephone) + uuido

def auto_manage_memory(telephone):
    """
    Maneja el estado de memoria de la conversación, incluyendo el manejo de encuesta, 
    actualización de image_url y template_sid.

    Args:
        telephone (str): Número de teléfono asociado al usuario.
    Returns:
        tuple: Estado de la conversación, valores de encuesta, URL y template SID.
    """
    if not telephone or not isinstance(telephone, str):
        print(f"[Error] Número de teléfono inválido: {telephone}")
        return None, None, None, None, None, create_telephone_uuid(telephone)

    # Recuperar estado actual de la base de datos
    query = f"SELECT * FROM checkpoints WHERE Thread_id LIKE '%{telephone}%'"
    try:
        with closing(sqlite3.connect(db_path, check_same_thread=False)) as conn:
            conn.execute('PRAGMA wal_checkpoint;')
            df_checkpoints = pd.read_sql(query, conn)
    except Exception as e:
        print(f"Error al consultar la base de datos: {e}")
        return None, None, None, None, None, create_telephone_uuid(telephone)

    if df_checkpoints.empty:
        print(f"[Info] No se encontraron checkpoints para {telephone}.")
        return None, None, None, None, None, create_telephone_uuid(telephone)

    # Deserializar los datos
    try:
        channel_values = deserialize_dataframe(df_checkpoints).iloc[-1]['checkpoint'].get('channel_values')
        the_end = channel_values.get('the_end', None)
        human = channel_values.get('human', None)
        encuesta = channel_values.get('survey', None)
        template_sid = channel_values.get('template_sid', None)  # Extraer template_sid del estado
    except Exception as e:
        print(f"[Error] Fallo al deserializar los datos: {e}")
        return None, None, None, None, None, create_telephone_uuid(telephone)

    # Obtener image_url
    image_url = channel_values.get('url')
    print("URL ENCONTRADA: ", image_url)
    print("TEMPLATE SID ENCONTRADO: ", template_sid)

    auto_manage_timer(telephone, the_end, human, encuesta)
    
    if encuesta:
        print(f"[Auto Memory] Encuesta en progreso para {telephone}.")
        return False, False, image_url, True, template_sid, df_checkpoints['thread_id'].iloc[-1]
    elif the_end:
        print(f"[Auto Memory] Se finalizó la conversación")
        limpiar_checkpoints(df_checkpoints['thread_id'].iloc[-1])
        return False, False, image_url, False, template_sid, create_telephone_uuid(telephone)
    elif human:
        return False, True, image_url, False, template_sid, df_checkpoints['thread_id'].iloc[-1]
    else:
        return False, False, image_url, False, template_sid, df_checkpoints['thread_id'].iloc[-1]

# Funciones comunes
def guardar_conversacion(numero, mensaje, origen, old_thread_id):
    """
    Guarda la conversación en SQL Server.
    
    Args:
        numero (str): Número de teléfono del usuario
        mensaje (str): Mensaje enviado
        origen (str): Origen del mensaje (cliente/bot)
    """
    try:
        numero = str(numero).replace("whatsapp:+57", "")
        timestamp = datetime.now()        
        query = text("""
            INSERT INTO cob.conversaciones_chatbot (Numero, Mensaje, Origen, Timestamp, chat_id)
            VALUES (:numero, :mensaje, :origen, :timestamp, :thread_id)
        """)
        
        with engine.connect() as conn:
            conn.execute(query, {
                "numero": numero,
                "mensaje": mensaje,
                "origen": origen,
                "timestamp": timestamp,
                "thread_id": old_thread_id
            })
            conn.commit()
            
        print(f"[Guardar Conversación] {origen} -> {numero}: {mensaje}")
    except Exception as e:
        print(f"[Error] Error al guardar conversación: {str(e)}")

@app.post('/equirent')
async def equirent(
    request: Request,
    background_tasks: BackgroundTasks,
    Body: str = Form(None),
    From: str = Form(None),
    MediaUrl0: str = Form(None)
):
    try:
        # Obtener datos de la solicitud
        incoming_msg = Body.lower() if Body else ''
        from_number = From or ''
        media_url = MediaUrl0 or ''

        print(f"[EQUIRENT] Solicitud recibida: {incoming_msg} de {from_number}")

        # Manejar estado inicial
        the_end, human, image_url, encuesta, template_sid, old_thread_id = auto_manage_memory(from_number)
        print(f"[EQUIRENT] Estado inicial: the_end={the_end}, human={human}, encuesta={encuesta}, template_sid={template_sid}, thread_id={old_thread_id}")

        background_tasks.add_task(guardar_conversacion, from_number, incoming_msg, 'cliente', old_thread_id)

        # Actualizar estados del grafo
        update_states = {
            "the_end": the_end,
            "human": human,
            "survey": encuesta if encuesta is not None else False
        }
    
        config = {"configurable": {"thread_id": old_thread_id}}
        graph.update_state(config, update_states)

        # Verificar si ya está en multiagente o si el estado es human=True
        if cache_sac.get(from_number) == "multiagente" or human:
            print('Redireccionando al Multiagente', cache_sac)
            if cache_sac.get(from_number) == "multiagente":
                del cache_sac[from_number]
            return await manejar_transferencia_multiagente(from_number, incoming_msg, old_thread_id, media_url)

        # Generar respuesta principal
        response_message = main(from_number, incoming_msg, graph, old_thread_id)
        print(f"[EQUIRENT] Respuesta generada: {response_message}")

        # Verificar estado post-respuesta
        the_end, human, image_url, encuesta, template_sid, old_thread_id = auto_manage_memory(from_number)
        print(f"[EQUIRENT] Estado actualizado: the_end={the_end}, human={human}, encuesta={encuesta}, template_sid={template_sid}, thread_id={old_thread_id}")
        
        # Determinar acción basada en estado
        if the_end:
            print('[Equirent]Finalizando conversación')
            await enviar_respuesta(from_number, response_message, image_url, media_url, template_sid, old_thread_id) 
            return await finalizar_conversacion(from_number, old_thread_id)
        elif human:
            print('[Equirent] Transferencia a multiagente')
            await enviar_respuesta(from_number, response_message, image_url, media_url, template_sid, old_thread_id)
            return await manejar_transferencia(from_number, incoming_msg, media_url, old_thread_id)
        elif encuesta:
            print('[Equirent] Encuesta detectada')
            await enviar_respuesta(from_number, response_message, image_url, media_url, template_sid, old_thread_id)
            return await manejar_encuesta(from_number, old_thread_id)
        
        # Enviar respuesta
        return await enviar_respuesta(from_number, response_message, image_url, media_url, template_sid, old_thread_id)

    except Exception as e:
        print(f"[Error] Error en el endpoint EQUIRENT: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

async def manejar_transferencia_multiagente(from_number, incoming_msg, old_thread_id, media_url):
    """
    Maneja la transferencia de mensajes al multiagente, asegurando que
    el estado se mantenga consistente.
    """
    try:
        payload = {"thread_id": old_thread_id, "from_number": from_number, "message": incoming_msg}
        if media_url:
            archivo_local = obtener_archivo(media_url, account_sid, auth_token)
            payload["media_url"] = archivo_local
        
        # Asegurar que el estado human=True se mantenga en el grafo
        config = {"configurable": {"thread_id": old_thread_id}}
        graph.update_state(config, {"human": True})
        
        # Marcar en cache que este usuario está en modo multiagente si no lo está ya
        if cache_sac.get(from_number) != "multiagente":
            cache_sac[from_number] = "multiagente"
            
        response = requests.post(f"{MULTIAGENTE_BASE_URL}/chatbot/webhook", json=payload)
        if response.status_code == 200:
            return Response(status_code=204)
        else:
            raise HTTPException(status_code=500, detail=f"Error: {response.text}")
    except Exception as e:
        print(f"[Error] Error en transferencia al multiagente: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

async def manejar_transferencia(from_number, incoming_msg, media_url, old_thread_id):
    print('OLD Thread id: ',old_thread_id)
    # Marcar en cache que este usuario está en modo multiagente
    cache_sac[from_number] = "multiagente"
    transfer_response = transfer_to_multiagent(from_number, incoming_msg, old_thread_id)
    if transfer_response:
        return Response(status_code=204)
    else:
        raise HTTPException(status_code=500, detail="Error en transferencia")

async def manejar_encuesta(from_number, old_thread_id):
    stop_inactivity_timer(old_thread_id[:22])
    config = {"configurable": {"thread_id": old_thread_id}}
    graph.update_state(config, {"survey": True})
    print(f"[Multiagent-to-End] Encuesta detectada y configurada en el grafo para {from_number}, {old_thread_id}.")
    return Response(status_code=204)

def limpiar_checkpoints(thread_id):
    """
    Elimina todos los checkpoints asociados a un thread_id.
    
    Args:
        thread_id (str): ID del hilo a limpiar
    """
    try:
        print(f"[Cleanup] Limpiando checkpoints para thread_id: {thread_id}")
        with closing(sqlite3.connect(db_path, check_same_thread=False)) as conn:
            cursor = conn.cursor()
            # Eliminar todos los checkpoints que contengan el número de teléfono
            telefono = thread_id[:22]  # Obtener solo la parte del teléfono
            cursor.execute('DELETE FROM checkpoints WHERE Thread_id LIKE ?', (f'%{telefono}%',))
            conn.commit()
        print(f"[Cleanup] Checkpoints eliminados para thread_id: {thread_id}")
    except Exception as e:
        print(f"[Error] Error al limpiar checkpoints: {str(e)}")

async def finalizar_conversacion(from_number, old_thread_id):
    stop_inactivity_timer(old_thread_id[:22])
    # Limpiar todos los checkpoints relacionados con este número
    limpiar_checkpoints(old_thread_id)
    print(f"[EQUIRENT] Conversación finalizada para {from_number}.")
    return Response(status_code=204)

async def enviar_respuesta(to_number, response_message, image_url, media_url, template_sid=None, old_thread_id=None):
    """
    Envía respuesta al usuario usando Twilio, soportando mensajes normales, 
    imágenes y templates.

    Args:
        to_number (str): Número de teléfono del destinatario
        response_message (str): Mensaje a enviar
        image_url (str): URL de la imagen a enviar
        media_url (str): URL del media adjunto
        template_sid (str): SID del template de Twilio a usar
    """
    print(f"Usando número: '{TWILIO_WHATSAPP_NUMBER}'")
    try:
        if template_sid:
            # Enviar mensaje usando template
            client.messages.create(
                content_sid=template_sid,
                from_=TWILIO_WHATSAPP_NUMBER,
                to=to_number
            )
            guardar_conversacion(to_number, "Template message sent", "bot", old_thread_id)
        elif image_url:
            # Enviar mensaje con imagen
            message = limit_message_length(response_message)
            client.messages.create(
                body=message,
                media_url=[image_url],
                from_=TWILIO_WHATSAPP_NUMBER,
                to=to_number
            )
            guardar_conversacion(to_number, f"{message} [with image]", "bot", old_thread_id)
        else:
            # Enviar mensaje de texto normal
            message = limit_message_length(response_message)
            client.messages.create(
                body=message,
                from_=TWILIO_WHATSAPP_NUMBER,
                to=to_number
            )
            guardar_conversacion(to_number, message, "bot", old_thread_id)
        return Response(status_code=204)
    except Exception as e:
        print(f"[Error] Error al enviar respuesta: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post('/multiagent-to-whatsapp')
async def multiagent_to_whatsapp(request: Request):
    data = await request.json()
    to_number = data.get('to_number')
    message = data.get('message')
    media_url = data.get('media_url')

    if not to_number or not message:
        raise HTTPException(status_code=400, detail="Parámetros faltantes")
    
    try:
        # Si hay un archivo adjunto (media_url), enviarlo junto con el mensaje
        if media_url:
            client.messages.create(
                body=limit_message_length(message),
                media_url=[media_url],
                from_=TWILIO_WHATSAPP_NUMBER,
                to=to_number
            )
        else:
            # Si no hay archivo adjunto, solo enviar el mensaje de texto
            client.messages.create(
                body=limit_message_length(message),
                from_=TWILIO_WHATSAPP_NUMBER,
                to=to_number
            )
        
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post('/multiagent-to-end')
async def multiagent_to_end(request: Request):
    """
    Endpoint para gestionar el flujo desde multiagente al chatbot e iniciar automáticamente
    el flujo de encuesta sin requerir interacción adicional del usuario.
    """
    data = await request.json()
    print('[Multiagent-to-End] Datos recibidos:', data)
    to_number = data.get('to_number')
    message = data.get('message')
    thread_id = data.get('thread_id')

    if not to_number or not message:
        raise HTTPException(status_code=400, detail="Parámetros faltantes")

    try:
        # Configurar estado de encuesta
        config = {"configurable": {"thread_id": thread_id}}
        graph.update_state(config, {"survey": True})
        
        print(f"[Multiagent-to-End] Encuesta configurada en el grafo para {to_number}")

        # Mensaje de transición
        transition_message = (
            "¡Gracias por contactarnos! Para mejorar nuestro servicio, nos gustaría conocer tu opinión."
        )
        
        # Enviar mensaje de transición
        client.messages.create(
            body=limit_message_length(transition_message),
            from_=TWILIO_WHATSAPP_NUMBER,
            to=to_number
        )

        # Obtener el resultado del nodo de encuesta
        result = graph.invoke(
            {"messages": [HumanMessage(content="iniciar_encuesta")], "telephone": to_number},
            config,
            stream_mode="values"
        )

        # Enviar template de encuesta
        client.messages.create(
            from_=TWILIO_WHATSAPP_NUMBER,
            to=to_number,
            content_sid=result.get('template_sid')
        )

        cache_sac[to_number] = 'encuesta'
        return {"success": True, "message": "Flujo de encuesta iniciado"}

    except Exception as e:
        print(f"[Encuesta] Error al iniciar encuesta para {to_number}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

import signal
import sys
def signal_handler(sig, frame):
    print("\nCtrl+C detected! Exiting... in twilio app")
    sys.exit(0)  # Exit the script gracefully

# Attach the signal handler to SIGINT
signal.signal(signal.SIGINT, signal_handler)

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=5000)
