from typing import Dict
from langchain_core.messages import AIMessage
from tools.api_tools.cliente import get_maturity_by_vehicle_id
from tools.api_tools.auth_token import get_auth_token_api

def create_vehicle_documents_agent():
    def handle_documents(state: Dict) -> Dict:
        vehicle_info = state.get("vehicle_info", {})
        product_info = vehicle_info.get("product_info", {})
        
        if not product_info:
            return {
                "next": "vehicle_plate",
                "pending_agent": "vehicle_documents",
                "should_wait_for_input": True
            }
        
        try:
            token = get_auth_token_api()
            
            # Consultar SOAT
            soat_info = get_maturity_by_vehicle_id(
                vehn_id=product_info["vehn_id"],
                tdon_id="SOAT",  # Identificador para SOAT
                token=token
            )
            
            # Consultar Tecno-mecánica
            tecno_info = get_maturity_by_vehicle_id(
                vehn_id=product_info["vehn_id"],
                tdon_id="TECNO",  # Identificador para Tecno-mecánica
                token=token
            )
            
            return {
                "messages": [
                    # SOAT response
                    AIMessage(content=soat_info.get('message', 'Información no disponible')),
                    # Tecno response
                    AIMessage(content=tecno_info.get('message', 'Información no disponible'))
                ],
                "vehicle_info": {
                    **vehicle_info,
                    "documents_info": {
                        "soat": soat_info,
                        "tecno": tecno_info
                    }
                },
                "should_wait_for_input": False,
                "next": "supervisor"
            }
            
        except Exception as e:
            return {
                "messages": [AIMessage(content="Lo siento, hubo un error al consultar la información de los documentos. Por favor, intenta nuevamente.")],
                "should_wait_for_input": True
            }
    
    return handle_documents
