import requests

def get_auth_token_api():
    """
    Autentica con la API para obtener el token de autorización.

    Returns:
        str: Token de autorización.
    """
    url = "https://www.equirent.com.co/API/administracion/autenticar/credencialesbot"
    payload = {
        "strUsuario": "UsuarioProveedorEquiSoft_2",
        "strContrasena": "087e5437f177a384fe2fd1b6002848f6f7c55998",
        "strNIT": "UsuarioProveedorEquiSoft_2",
        "strRazonSocial": ""
    }
    headers = {"Content-Type": "application/json"}
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    print("Respuesta completa:", response.json())
    token = response.json().get("StrToken")
    print("StrToken:", token)
    return token