from typing import Dict
from datetime import datetime
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate
from config.llm import llm

from tools.api_tools.loguer import validate_cliente_api
from tools.api_tools.auth_token import get_auth_token_api
from .client.policy_agent import create_policy_agent
from .client.soat_agent import create_soat_agent
from .client.account_manager_agent import create_account_manager_agent
from .client.insurance_info_agent import create_insurance_agent
from .client.workshop_agent import create_workshop_agent
from .client.branch_agent import create_branch_agent
from .client.update_info_agent import create_update_info_agent

# Templates para el LLM
CLIENT_INTENT_TEMPLATE = """Analiza la consulta del cliente y determina qué tipo de información necesita.

Mensaje del usuario: {user_message}

Categorías de consulta:
1. POLICY - Consultas sobre pólizas de vehículos
2. SOAT - Verificación de SOAT
3. ACCOUNT_MANAGER - Información del gestor de cuenta
4. INSURANCE - Asistencia de seguros
5. WORKSHOP - Citas en talleres
6. BRANCH - Información de sucursales
7. UPDATE_INFO - Actualización de datos

También detecta si:
- El usuario quiere consultar otro vehículo o menciona otra placa
- Menciona "cambiar de vehículo", "otra placa", "otro carro", etc.

Responde con un JSON:
{
    "category": str,
    "requires_vehicle_info": bool,
    "needs_new_plate": bool,
    "confidence": float
}"""

def create_client_agent():
    # Crear instancias de los agentes especializados
    policy_agent = create_policy_agent()
    soat_agent = create_soat_agent()
    account_manager_agent = create_account_manager_agent()
    insurance_agent = create_insurance_agent()
    workshop_agent = create_workshop_agent()
    branch_agent = create_branch_agent()
    update_info_agent = create_update_info_agent()
    
    def handle_client_services(state: Dict) -> Dict:
        messages = state.get("messages", [])
        human_messages = [m for m in messages if isinstance(m, HumanMessage)]
        
        if not human_messages:
            return {
                "messages": [AIMessage(content="¿En qué puedo ayudarte con tu vehículo?")],
                "should_wait_for_input": True
            }
        
        last_message = human_messages[-1].content
        client_session = state.get("client_session")
        
        # Verificar si necesitamos iniciar sesión
        if not client_session:
            # Si no hay intentos previos de autenticación
            if not state.get("auth_attempts"):
                return {
                    "messages": [AIMessage(content="Por favor, proporciona tu número de documento para acceder a la información de tu vehículo.")],
                    "should_wait_for_input": True,
                    "auth_attempts": 1
                }
            
            # Intentar autenticar con el último mensaje
            try:
                token = get_auth_token_api()
                client_info = validate_cliente_api(last_message, token)
                
                if client_info:
                    # Autenticación exitosa
                    return {
                        "messages": [AIMessage(content="Autenticación exitosa. ¿Sobre qué vehículo deseas consultar? Por favor, proporciona la placa.")],
                        "should_wait_for_input": True,
                        "client_session": {
                            "document": last_message,
                            "timestamp": datetime.now().isoformat(),
                            "client_info": client_info
                        },
                        "active_role": "client",
                        "needs_plate": True
                    }
                else:
                    # Autenticación fallida
                    return {
                        "messages": [AIMessage(content="No se encontró información para el documento proporcionado. Por favor, verifica e intenta nuevamente.")],
                        "should_wait_for_input": True,
                        "auth_attempts": state.get("auth_attempts", 0) + 1
                    }
            except Exception as e:
                return {
                    "messages": [AIMessage(content="Hubo un error al validar tu información. Por favor, intenta nuevamente.")],
                    "should_wait_for_input": True
                }
        
        # Manejar solicitud o cambio de placa
        if state.get("needs_plate") or (not state.get("vehicle_info") and state.get("plate_requested")):
            # Validar formato de placa (validación básica)
            if len(last_message.strip()) >= 6:  # Longitud mínima de una placa
                return {
                    "vehicle_info": {"plate": last_message.strip().upper()},
                    "needs_plate": False,
                    "plate_requested": False,
                    "messages": [AIMessage(content="Gracias. ¿En qué puedo ayudarte con este vehículo?")],
                    "should_wait_for_input": True
                }
            else:
                return {
                    "messages": [AIMessage(content="Por favor, proporciona una placa válida.")],
                    "should_wait_for_input": True,
                    "needs_plate": True
                }
        
        # Si ya hay sesión, analizar la intención
        prompt = ChatPromptTemplate.from_template(CLIENT_INTENT_TEMPLATE)
        chain = prompt | llm.with_structured_output({
            "category": str,
            "requires_vehicle_info": bool,
            "needs_new_plate": bool,
            "confidence": float
        })
        
        result = chain.invoke({"user_message": last_message})
        
        # Si el usuario quiere consultar otro vehículo
        if result.get("needs_new_plate", False):
            return {
                "messages": [AIMessage(content="Entiendo que quieres consultar otro vehículo. Por favor, proporciona la placa del vehículo que deseas consultar.")],
                "should_wait_for_input": True,
                "needs_plate": True
            }
        
        # Si necesitamos información del vehículo y no la tenemos
        if result["requires_vehicle_info"] and not state.get("vehicle_info"):
            # Redirigir al flujo de captura de placa
            return {
                "messages": [AIMessage(content="Para brindarte esa información, necesito la placa del vehículo. Por favor, proporcióname la placa.")],
                "should_wait_for_input": True,
                "needs_plate": True
            }
        
        # Dirigir a los agentes especializados según la categoría
        if result["category"] == "POLICY":
            return policy_agent(state)
        elif result["category"] == "SOAT":
            return soat_agent(state)
        elif result["category"] == "ACCOUNT_MANAGER":
            return account_manager_agent(state)
        elif result["category"] == "INSURANCE":
            return insurance_agent(state)
        elif result["category"] == "WORKSHOP":
            return workshop_agent(state)
        elif result["category"] == "BRANCH":
            return branch_agent(state)
        elif result["category"] == "UPDATE_INFO":
            return update_info_agent(state)
        
        # Si no se identifica una categoría clara
        return {
            "messages": [AIMessage(content="""
                No estoy seguro de qué información necesitas. ¿Podrías especificar si necesitas ayuda con:
                • Información de pólizas
                • Verificación de SOAT
                • Contacto con tu gestor
                • Asistencia de seguros
                • Citas en talleres
                • Información de sucursales
                • Actualización de datos
            """)],
            "should_wait_for_input": True
        }
    
    return handle_client_services
