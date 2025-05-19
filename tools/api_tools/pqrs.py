import requests
from tools.api_tools.auth_token import get_auth_token_api

def add_pqrs_case():
    """
    Crea un nuevo caso PQRS a través de la API.

    Returns:
        str: Token de autorización.
    """
    try:
        # Primero obtener el token de autorización
        token = get_auth_token_api()
        
        url = "https://www.equirent.com.co/API/IntegracionEQ/addcasoPQRS"
        payload = {
            "tipoComunicacion": "otro",
            "nombre": "Leonardo Gomez",
            "email": "leonardo.gomez@equirent.com.co",
            "celular": "345324234",
            "ciudad": "Bogota",
            "empresa": "Equirent",
            "descripcion": "pruebas caso equisoft",
            "extensionAdjunto": "",
            "adjunto": ""
        }
        
        # Agregar el token al header de autorización
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
        
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        print("Respuesta completa:", response.json())
        return response.json()
        
    except requests.RequestException as e:
        print(f"Error en la petición: {str(e)}")
        return None