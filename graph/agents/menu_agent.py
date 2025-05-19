from typing import Dict
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate
from config.llm import llm

MENU_TEMPLATE = """Analiza la solicitud del usuario y determina qué opción del menú es más relevante.

Mensaje del usuario: {user_message}

Opciones disponibles:
1. Iniciar sesión o registro
2. Consultar pagos y facturas
3. Soporte y ayuda

Responde con un JSON:
{
    "selected_option": str,
    "confidence": float,
    "needs_clarification": bool
}"""

def create_menu_agent():
    def handle_menu(state: Dict) -> Dict:
        messages = state.get("messages", [])
        human_messages = [m for m in messages if isinstance(m, HumanMessage)]
        
        # Primer mensaje - mostrar menú
        if not human_messages:
            return {
                "next": "menu",
                "messages": [AIMessage(content="""
                    ¿En qué puedo ayudarte hoy?
                    
                    1. Iniciar sesión o registro
                    2. Consultar pagos y facturas
                    3. Soporte y ayuda
                    
                    Por favor, indica qué necesitas.
                """)],
                "should_wait_for_input": True
            }
        
        last_message = human_messages[-1].content
        
        # Analizar selección del usuario
        prompt = ChatPromptTemplate.from_template(MENU_TEMPLATE)
        chain = prompt | llm.with_structured_output({
            "selected_option": str,
            "confidence": float,
            "needs_clarification": bool
        })
        
        result = chain.invoke({"user_message": last_message})
        
        if result["needs_clarification"]:
            return {
                "next": "menu",
                "messages": [AIMessage(content="No estoy seguro de qué opción necesitas. ¿Podrías ser más específico?")],
                "should_wait_for_input": True
            }
        
        next_state = {
            "1": "login",
            "2": "collection",
            "3": "support"
        }.get(result["selected_option"], "menu")
        
        return {
            "next": next_state,
            "messages": [AIMessage(content=f"Te ayudaré con {next_state}")],
            "should_wait_for_input": True,
            "current_state": next_state
        }
    
    return handle_menu