from typing import Dict
from langchain_core.messages import AIMessage
from tools.api_tools.cliente import get_product_by_plate_api
from tools.api_tools.auth_token import get_auth_token_api

def create_product_info_agent():
    def handle_product_info(state: Dict) -> Dict:
        client_session = state.get("client_session")
        vehicle_info = state.get("vehicle_info")
        
        if not vehicle_info or not vehicle_info.get("plate"):
            return {
                "messages": [AIMessage(content="Por favor, proporciona la placa del vehículo para consultar su información.")],
                "should_wait_for_input": True
            }
        
        try:
            token = get_auth_token_api()
            product_info = get_product_by_plate_api(
                document=client_session["document"],
                plate=vehicle_info["plate"],
                token=token
            )
            
            # Guardar información del producto en el estado
            return {
                "messages": [AIMessage(content=f"""
                    Información del vehículo:
                    • Placa: {product_info.get('placa', 'No disponible')}
                    • Producto: {product_info.get('producto', 'No disponible')}
                    • Estado: {product_info.get('estado', 'No disponible')}
                """)],
                "vehicle_info": {
                    **vehicle_info,
                    "product_info": product_info
                },
                "should_wait_for_input": False,
                "next": "supervisor"
            }
            
        except Exception as e:
            return {
                "messages": [AIMessage(content="Lo siento, hubo un error al consultar la información del vehículo. Por favor, intenta nuevamente.")],
                "should_wait_for_input": True
            }
    
    return handle_product_info