from typing import Dict
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate
from config.llm import llm

PLATE_INTENT_TEMPLATE = """Analiza si el usuario está mencionando o solicitando información sobre una placa de vehículo diferente.

Mensaje del usuario: {user_message}

Considera:
- Menciones directas de placas
- Solicitudes de cambio de vehículo
- Referencias a "otro carro", "otro vehículo"
- Números de placa en cualquier formato

Responde con un JSON:
{
    "needs_new_plate": bool,
    "plate_mentioned": str or null,
    "confidence": float
}"""

def create_vehicle_plate_agent():
    def handle_plate_request(state: Dict) -> Dict:
        messages = state.get("messages", [])
        human_messages = [m for m in messages if isinstance(m, HumanMessage)]
        current_plate = state.get("vehicle_info", {}).get("plate")
        
        if not human_messages:
            return {
                "messages": [AIMessage(content="Por favor, indícame la placa del vehículo sobre el cual deseas consultar.")],
                "should_wait_for_input": True
            }
        
        last_message = human_messages[-1].content
        
        # Si no hay placa actual, es la primera solicitud
        if not current_plate:
            # Validar formato de placa (puedes expandir esta validación)
            if len(last_message.strip()) >= 6:  # Longitud mínima de una placa
                return {
                    "vehicle_info": {"plate": last_message.strip().upper()},
                    "next": state.get("pending_agent", "supervisor"),
                    "should_wait_for_input": False
                }
            else:
                return {
                    "messages": [AIMessage(content="Por favor, proporciona una placa válida.")],
                    "should_wait_for_input": True
                }
        
        # Analizar si el usuario quiere cambiar de placa
        prompt = ChatPromptTemplate.from_template(PLATE_INTENT_TEMPLATE)
        chain = prompt | llm.with_structured_output({
            "needs_new_plate": bool,
            "plate_mentioned": str,
            "confidence": float
        })
        
        result = chain.invoke({"user_message": last_message})
        
        if result["needs_new_plate"]:
            if result["plate_mentioned"]:
                # Si mencionó una nueva placa, actualizar y continuar
                return {
                    "vehicle_info": {"plate": result["plate_mentioned"].upper()},
                    "next": state.get("pending_agent", "supervisor"),
                    "should_wait_for_input": False
                }
            else:
                # Si necesita nueva placa pero no la mencionó, solicitarla
                return {
                    "messages": [AIMessage(content="Por favor, indícame la placa del vehículo que deseas consultar.")],
                    "should_wait_for_input": True
                }
        
        # Si no necesita cambio de placa, continuar con el flujo normal
        return {
            "next": state.get("pending_agent", "supervisor"),
            "should_wait_for_input": False
        }
    
    return handle_plate_request