from typing import Dict
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate
from config.llm import llm

POLICY_INTENT_TEMPLATE = """Analiza si el usuario está aceptando las políticas de uso.

Mensaje del usuario: {user_message}

Considera como aceptación:
- "Sí acepto"
- "Acepto"
- "De acuerdo"
- "Estoy de acuerdo"
- "Ok"
- Variaciones afirmativas claras

Responde con un JSON:
{
    "accepted": true/false,
    "confidence": float entre 0 y 1
}"""

def create_policy_agent():
    def handle_policies(state: Dict) -> Dict:
        messages = state.get("messages", [])
        human_messages = [m for m in messages if isinstance(m, HumanMessage)]
        
        # Primer mensaje - mostrar políticas
        if not human_messages:
            return {
                "next": "policies",
                "messages": [AIMessage(content="""
                    Antes de comenzar, necesito que aceptes nuestras políticas de uso:
                    
                    1. Tratamiento de datos personales
                    2. Términos y condiciones del servicio
                    3. Políticas de privacidad
                    
                    ¿Aceptas estas políticas?
                """)],
                "should_wait_for_input": True
            }
        
        last_message = human_messages[-1].content
        
        # Analizar intención de aceptación
        prompt = ChatPromptTemplate.from_template(POLICY_INTENT_TEMPLATE)
        chain = prompt | llm.with_structured_output({
            "accepted": bool,
            "confidence": float
        })
        
        result = chain.invoke({"user_message": last_message})
        
        if result["accepted"] and result["confidence"] > 0.7:
            return {
                "next": "menu",
                "messages": [AIMessage(content="¡Gracias por aceptar! ¿En qué puedo ayudarte hoy?")],
                "should_wait_for_input": True,
                "policies_accepted": True,
                "current_state": "menu"
            }
        else:
            return {
                "next": "policies",
                "messages": [AIMessage(content="Por favor, necesito que aceptes explícitamente las políticas para continuar. ¿Estás de acuerdo con ellas?")],
                "should_wait_for_input": True
            }
    
    return handle_policies