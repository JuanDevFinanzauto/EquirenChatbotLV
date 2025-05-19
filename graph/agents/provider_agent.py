from typing import Dict
from datetime import datetime, timedelta
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate
from config.llm import llm

from tools.api_tools.loguer import validate_proveedor_api
from tools.api_tools.auth_token import get_auth_token_api

# Templates para el LLM
PROVIDER_INTENT_TEMPLATE = """Analiza la consulta del proveedor y determina qué tipo de información necesita.

Mensaje del usuario: {user_message}

Categorías de consulta:
1. CLOSING_DATES - Consultas sobre fechas de cierre
2. INVOICE_STATUS - Verificación del estado de facturas
3. EQUISOFT_ACCESS - Acceso a la plataforma Equisoft
4. USER_ACCOUNT - Solicitudes de cuentas de usuario
5. PAYMENT_INFO - Información de pagos
6. SUPPORT - Soporte técnico Equisoft
7. UPDATE_INFO - Actualización de datos

Responde con un JSON:
{
    "category": str,
    "requires_invoice_info": bool,
    "confidence": float
}"""

def create_provider_agent():
    def handle_provider_services(state: Dict) -> Dict:
        messages = state.get("messages", [])
        human_messages = [m for m in messages if isinstance(m, HumanMessage)]
        
        if not human_messages:
            return {
                "messages": [AIMessage(content="¿En qué puedo ayudarte con tus servicios de proveedor?")],
                "should_wait_for_input": True
            }
        
        last_message = human_messages[-1].content
        provider_session = state.get("provider_session")
        
        # Verificar si necesitamos iniciar sesión
        if not provider_session:
            # Si no hay intentos previos de autenticación
            if not state.get("auth_attempts"):
                return {
                    "messages": [AIMessage(content="Por favor, proporciona tu número de documento para acceder a la información de proveedor.")],
                    "should_wait_for_input": True,
                    "auth_attempts": 1
                }
            
            # Intentar autenticar con el último mensaje
            try:
                token = get_auth_token_api()
                provider_info = validate_proveedor_api(last_message, token)
                
                if provider_info:
                    # Autenticación exitosa
                    return {
                        "messages": [AIMessage(content="Autenticación exitosa. ¿En qué puedo ayudarte con tus servicios de proveedor?")],
                        "should_wait_for_input": True,
                        "provider_session": {
                            "document": last_message,
                            "timestamp": datetime.now().isoformat(),
                            "provider_info": provider_info
                        },
                        "active_role": "provider"
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
        
        # Si ya hay sesión, analizar la intención
        prompt = ChatPromptTemplate.from_template(PROVIDER_INTENT_TEMPLATE)
        chain = prompt | llm.with_structured_output({
            "category": str,
            "requires_invoice_info": bool,
            "confidence": float
        })
        
        result = chain.invoke({"user_message": last_message})
        
        # Si necesitamos información de factura y no la tenemos
        if result["requires_invoice_info"] and not state.get("invoice_info"):
            return {
                "messages": [AIMessage(content="Por favor, proporciona el número de factura para poder ayudarte.")],
                "should_wait_for_input": True
            }
        
        # Determinar el siguiente agente basado en la categoría
        next_agent = {
            "CLOSING_DATES": "closing_dates_agent",
            "INVOICE_STATUS": "invoice_status_agent",
            "EQUISOFT_ACCESS": "equisoft_access_agent",
            "USER_ACCOUNT": "user_account_agent",
            "PAYMENT_INFO": "payment_info_agent",
            "SUPPORT": "support_agent",
            "UPDATE_INFO": "update_info_agent"
        }.get(result["category"])
        
        if next_agent:
            return {
                "next": next_agent,
                "messages": [AIMessage(content="Te ayudaré con esa información...")],
                "should_wait_for_input": False
            }
        
        # Si no se identifica una categoría clara
        return {
            "messages": [AIMessage(content="""
                No estoy seguro de qué información necesitas. ¿Podrías especificar si necesitas ayuda con:
                • Fechas de cierre
                • Estado de facturas
                • Acceso a Equisoft
                • Solicitud de cuenta de usuario
                • Información de pagos
                • Soporte técnico
                • Actualización de datos
            """)],
            "should_wait_for_input": True
        }
    
    return handle_provider_services