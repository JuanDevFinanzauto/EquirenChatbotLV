import requests
def validate_cliente_api(documento, token):
    """
    Valida la existencia de un cliente por documento.

    Args:
        documento (str): Número de documento del cliente.
        token (str): Token de autorización.

    Returns:
        dict: Respuesta de la API con información del cliente.
    """
    url = f"https://www.equirent.com.co/API/automatizacion/GetClienteXDocumentoBot?strDocumento={documento}"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    print("Respuesta de la api: ",response.json)
    return response.json()

def validate_proveedor_api(documento, token):
    """
    Valida la existencia de un proveedor por documento.

    Args:
        documento (str): Número de documento del proveedor.

    Returns:
        dict: Respuesta de la API con información del proveedor.
    """
    url = f"https://www.equirent.com.co/API/automatizacion/getProveedorXDocumentoBot?strDocumento={documento}"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    print("Respuesta de la api: ",response.json)
    return response.json()