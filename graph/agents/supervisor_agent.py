from typing import Dict
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langchain_core.prompts import ChatPromptTemplate
from config.llm import llm  # Importamos el LLM centralizado

class ConversationState:
    INITIAL = "initial"
    POLICIES = "policies"
    GREETING = "greeting"
    MENU = "menu"
    LOGIN = "login"
    COLLECTION = "collection"
    SUPPORT = "support"
    GENERAL_INQUIRY = "general_inquiry"
    PQRS = "pqrs"
    TRANSFER = "transfer"
    NEW_CLIENT = "new_client"
    CLIENT_SERVICES = "client_services"
    PROVIDER_SERVICES = "provider_services"

# Template para analizar la intención del usuario
SUPERVISOR_TEMPLATE = """Eres un agente supervisor de Equirent, empresa líder en renting de vehículos. 
Analiza el mensaje del usuario y determina el flujo más apropiado.

Estado actual: {current_state}
Historial de mensajes previos: {message_history}
Último mensaje del usuario: {user_message}

Determina la siguiente acción basada en estas categorías:

1. LOGIN - Si el usuario:
   - Se identifica como cliente o proveedor actual
   - Necesita consultar información específica de cliente/proveedor
   - Menciona consultas sobre pólizas, SOAT, facturas, etc.

2. COLLECTION - Si el usuario:
   - Menciona pagos, facturas o cobranza
   - Necesita información sobre estados de cuenta
   - Tiene dudas sobre fechas de pago o vencimientos

3. GENERAL_INQUIRY - Si el usuario:
   - Hace preguntas generales sobre Equirent
   - Consulta sobre servicios de renting
   - Solicita información sobre sucursales
   - No requiere autenticación para su consulta

4. PQRS - Si el usuario:
   - Quiere presentar una queja
   - Tiene una petición formal
   - Desea hacer un reclamo
   - Quiere hacer una sugerencia

5. NEW_CLIENT - Si el usuario:
   - Muestra interés en ser cliente
   - Pregunta sobre cómo adquirir servicios
   - Solicita cotizaciones

6. SUPPORT - Si el usuario:
   - Necesita ayuda técnica
   - Reporta problemas con un vehículo
   - Requiere asistencia en carretera
   - Menciona emergencias

7. TRANSFER - Si el usuario:
   - Solicita hablar con un asesor humano
   - Requiere atención personalizada
   - La consulta es muy específica o compleja

8. MENU - Si no está claro o necesita ver opciones disponibles

Responde con un JSON:
{
    "next_state": "estado_siguiente",
    "response": "mensaje para el usuario explicando por qué se le dirige a ese flujo",
    "requires_input": true/false,
    "confidence": float entre 0 y 1
}"""

def create_supervisor_agent():
    def analyze_conversation(state: Dict) -> Dict:
        # Obtener mensajes del estado
        messages = state.get("messages", [])
        
        # Obtener el último mensaje del usuario
        human_messages = [m for m in messages if isinstance(m, HumanMessage)]
        if not human_messages:
            return {
                "next": "policies",
                "messages": [AIMessage(content="¡Hola! Antes de comenzar, necesito que aceptes nuestras políticas de uso. ¿Estás de acuerdo?")],
                "should_wait_for_input": True,
                "current_state": ConversationState.POLICIES
            }
        
        last_message = human_messages[-1].content
        current_state = state.get("current_state", ConversationState.INITIAL)
        
        # Crear el historial de mensajes para contexto
        message_history = "\n".join([
            f"{'Bot' if isinstance(m, AIMessage) else 'Usuario'}: {m.content}"
            for m in messages[-5:]  # Últimos 5 mensajes para contexto
        ])
        
        # Procesar políticas si es el estado inicial o de políticas
        if current_state in [ConversationState.INITIAL, ConversationState.POLICIES]:
            if "acepto" in last_message.lower() or "sí" in last_message.lower() or "si" in last_message.lower():
                return {
                    "next": "greeting",
                    "messages": [AIMessage(content="""
                    ¡Hola! Soy el asistente virtual de Equirent 🚗
                    
                    Puedo ayudarte con:
                    • Consultas sobre nuestros servicios de renting
                    • Información para clientes y proveedores
                    • Pagos y facturas
                    • Soporte técnico y asistencia
                    • Presentar PQRS
                    • Contacto con asesores
                    
                    ¿En qué puedo ayudarte hoy?
                    """)],
                    "should_wait_for_input": True,
                    "policies_accepted": True,
                    "current_state": ConversationState.GREETING
                }
            else:
                return {
                    "next": "policies",
                    "messages": [AIMessage(content="Para continuar, necesito que aceptes explícitamente nuestras políticas. ¿Estás de acuerdo?")],
                    "should_wait_for_input": True,
                    "current_state": ConversationState.POLICIES
                }
        
        # Si es la primera interacción después del saludo
        if current_state == ConversationState.GREETING:
            # Pasar al menú después del saludo
            current_state = ConversationState.MENU
        
        # Si ya pasó las políticas, analizar la intención usando el LLM
        prompt = ChatPromptTemplate.from_template(SUPERVISOR_TEMPLATE)
        chain = prompt | llm.with_structured_output({
            "next_state": str,
            "response": str,
            "requires_input": bool,
            "confidence": float
        })
        
        result = chain.invoke({
            "current_state": current_state,
            "message_history": message_history,
            "user_message": last_message
        })
        
        # Si la confianza es baja, pedir clarificación
        if result.get("confidence", 0) < 0.7:
            return {
                "next": current_state,
                "messages": [AIMessage(content="""
                No estoy seguro de entender completamente tu solicitud. 
                ¿Podrías especificar si necesitas:
                
                1. Información general sobre nuestros servicios
                2. Acceder a tu información como cliente o proveedor
                3. Consultar pagos o facturas
                4. Soporte técnico o asistencia
                5. Presentar una PQRS
                6. Hablar con un asesor
                7. Información sobre cómo ser cliente
                """)],
                "should_wait_for_input": True,
                "current_state": current_state
            }
        
        # Manejar transiciones basadas en la intención
        return {
            "next": result["next_state"],
            "messages": [AIMessage(content=result["response"])],
            "should_wait_for_input": result["requires_input"],
            "current_state": result["next_state"]
        }
    
    return analyze_conversation
