from typing import Dict
from langchain_core.messages import AIMessage
from tools.api_tools.cliente import get_insurance_by_plate_api
from tools.api_tools.auth_token import get_auth_token_api

def create_insurance_agent():
    def handle_insurance(state: Dict) -> Dict:
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
            insurance_info = get_insurance_by_plate_api(
                vehn_id=product_info["vehn_id"],
                id_producto=product_info["id_producto"],
                token=token
            )
            
            return {
                "messages": [AIMessage(content=f"""
                    Información de tu seguro:
                    • Aseguradora: {insurance_info.get('aseguradora', 'No disponible')}
                    • Póliza: {insurance_info.get('poliza', 'No disponible')}
                    • Cobertura: {insurance_info.get('cobertura', 'No disponible')}
                    • Teléfono asistencia: {insurance_info.get('telefono_asistencia', 'No disponible')}
                    
                    Para asistencia 24/7, contacta directamente a tu aseguradora.
                """)],
                "vehicle_info": {
                    **vehicle_info,
                    "insurance_info": insurance_info
                },
                "should_wait_for_input": False,
                "next": "supervisor"
            }
            
        except Exception as e:
            return {
                "messages": [AIMessage(content="Lo siento, hubo un error al consultar la información del seguro. Por favor, intenta nuevamente.")],
                "should_wait_for_input": True
            }
    
    return handle_insurance