import requests

def get_product_by_plate_api(document, plate, token):
    """
    Valida el producto asociado a una placa específica de un cliente confirmado.

    Args:
        document (str): Documento del cliente.
        plate (str): Placa del vehículo.
        token (str): Token de autorización.

    Returns:
        dict: Información del producto asociado a la placa.
    """
    url = f"https://www.equirent.com.co/API/automatizacion/getProductoxPlacaBot?strDocumento={document}&strPlaca={plate}"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    print("Respuesta de la api: ",response.json)
    return response.json()

def get_account_manager_by_plate_api(vehn_id, id_producto, token):
    """
    Valida el ejecutivo de cuenta a una placa específica de un cliente confirmado.

    Args:
        document (str): Documento del cliente.
        plate (str): Placa del vehículo.
        token (str): Token de autorización.

    Returns:
        dict: Información del producto asociado a la placa.
    """
    url = f"https://www.equirent.com.co/API/automatizacion/getEjecutivoxPlacaBot?vehn_id={vehn_id}&idProducto={id_producto}"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    print("Respuesta de la api: ",response.json)
    return response.json()

def get_maturity_by_vehicle_id(vehn_id, tdon_id, token):
    """
    Valida el vencimiento de soat o tecnomecanica a una placa específica de un cliente confirmado.

    Args:
        tdon_id (str): Producto a consultar el vencimiento.
        vehn_id (str): Id del vehículo.
        token (str): Token de autorización.

    Returns:
        dict: Información del producto asociado a la placa.
    """
    url = f"https://rerun.com.co:10181/automatizacion/getVencimientoXIdPlacaBot?vehn_id={vehn_id}&tdon_id={tdon_id}"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    print('Respuesta api de vencimientos: ',response.json)
    return response.json()

def get_insurance_by_plate_api(vehn_id, id_producto, token):
    """
    Valida la aseguradora que se encuentra asociada a una placa específica de un cliente confirmado.

    Args:
        document (str): Documento del cliente.
        plate (str): Placa del vehículo.
        token (str): Token de autorización.

    Returns:
        dict: Información del producto asociado a la placa.
    """
    url = f"https://www.equirent.com.co/API/automatizacion/getAseguradoraXIdPlacaBot?vehn_id={vehn_id}&idProducto={id_producto}"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    print("Respuesta de la api: ",response.json)
    return response.json()