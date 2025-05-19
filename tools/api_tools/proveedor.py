import requests

def get_bill_reception_date_api(token):
    """
    Método para obtener la fecha de cierre de acuerdo al momento de la consulta.

    Args:
        token (str): Token de autorización.

    Returns:
        dict: Información del producto asociado a la placa.
    """
    url = f"https://www.equirent.com.co/API/automatizacion/getFechaRecepcionFacturasBot"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    print("Respuesta de la api: ",response.json)
    return response.json()

def get_bill_data_api(token: str, document: str, bill: str):
    """
    Método para obtener la informacion de una factura en el momento de la consulta.

    Args:
        token (str): Token de autorización.
        document (str): Documento del proveedor
        bill (str): Número de factura

    Returns:
        dict: Información de la factura asociado al usuario.
    """
    print('En la api de get_bill_data')
    url = f"https://www.equirent.com.co/API/automatizacion/getEstadoFacturaIndividualBot?strDocumento={document}&strFactura={bill}"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    print("Respuesta de la api: ",response.json)
    return response.json()