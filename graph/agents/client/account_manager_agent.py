from typing import Dict
from langchain_core.messages import AIMessage
from tools.api_tools.cliente import get_account_manager_by_plate_api
from tools.api_tools.auth_token import get_auth_token_api

def create_account_manager_agent():
    def handle_account_manager(state: Dict) -> Dict:
        vehicle_info = state.get("vehicle_info", {})
        product_info = vehicle_info.get("product_info", {})
        
        if not product_info:
            return {
                "messages": [AIMessage(content="Primero necesito obtener la información del vehículo. Por favor, proporciona la placa.")],
                "should_wait_for_input": True,
                "next": "product_info"
            }
        
        try:
            token = get_auth_token_api()
            manager_info = get_account_manager_by_plate_api(
                vehn_id=product_info["vehn_id"],
                id_producto=product_info["id_producto"],
                token=token
            )
            
            return {
                "messages": [AIMessage(content=f"""
                    Información de tu ejecutivo de cuenta:
                    • Nombre: {manager_info.get('nombre', 'No disponible')}
                    ��� Teléfono: {manager_info.get('telefono', 'No disponible')}
                    • Email: {manager_info.get('email', 'No disponible')}
                    • Horario: {manager_info.get('horario', 'No disponible')}
                """)],
                "vehicle_info": {
                    **vehicle_info,
                    "manager_info": manager_info
                },
                "should_wait_for_input": False,
                "next": "supervisor"
            }
            
        except Exception as e:
            return {
                "messages": [AIMessage(content="Lo siento, hubo un error al consultar la información del ejecutivo de cuenta. Por favor, intenta nuevamente.")],
                "should_wait_for_input": True
            }
    
    return handle_account_manager