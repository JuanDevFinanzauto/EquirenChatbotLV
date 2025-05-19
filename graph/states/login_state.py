from typing import Optional, Union, Sequence
from typing_extensions import TypedDict
from graph.state import GraphState

class LoginState(GraphState):
    """Estado específico para el proceso de login que extiende el estado general"""
    reintentos: Optional[int]
    client_info: Optional[dict]
    provider_info: Optional[dict]
    has_document: Optional[bool]