from typing import Dict
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage

from memory.redis_checkpoint import get_redis_checkpointer
from graph.state import GraphState
from graph.agents.policy_agent import create_policy_agent
from graph.agents.supervisor_agent import create_supervisor_agent
from graph.agents.client_agent import create_client_agent
from graph.agents.provider_agent import create_provider_agent


def build_graph(use_checkpoint: bool = False):
    """
    Construye el grafo con flujo completo de conversación y manejo de sesiones interno
    """
    try:
        checkpointer = get_redis_checkpointer(namespace="whatsapp_sessions") if use_checkpoint else None
    except Exception as e:
        print(f"Warning: Could not initialize Redis checkpoint: {e}")
        checkpointer = None

    # Crear el grafo principal
    builder = StateGraph(GraphState)
    
    # Crear agentes
    policy_agent = create_policy_agent()
    supervisor = create_supervisor_agent()
    client_agent = create_client_agent()
    provider_agent = create_provider_agent()
    
    # Agregar nodos
    builder.add_node("policies", policy_agent)
    builder.add_node("supervisor", supervisor)
    builder.add_node("client_services", client_agent)
    builder.add_node("provider_services", provider_agent)
    
    # Por implementar
    # builder.add_node("general_inquiry", create_general_inquiry_agent())
    # builder.add_node("pqrs", create_pqrs_agent())
    # builder.add_node("new_client", create_new_client_agent())
    # builder.add_node("transfer", create_transfer_agent())
    
    # Definir las transiciones
    # Desde políticas al supervisor
    builder.add_conditional_edges(
        "policies",
        lambda state: "supervisor" if state.get("policies_accepted") else "policies"
    )
    
    # Desde supervisor a los diferentes agentes
    builder.add_conditional_edges(
        "supervisor",
        lambda state: state.get("next", "supervisor")
    )
    
    # Desde los agentes especializados de vuelta al supervisor
    builder.add_edge("client_services", "supervisor")
    builder.add_edge("provider_services", "supervisor")
    # builder.add_edge("general_inquiry", "supervisor")
    # builder.add_edge("pqrs", "supervisor")
    # builder.add_edge("new_client", "supervisor")
    # builder.add_edge("transfer", "supervisor")
    
    # Configurar punto de entrada
    builder.set_entry_point("policies")
    
    # Configurar puntos de salida
    builder.add_edge("supervisor", END)

    # Compilar el grafo
    config = {
        "interrupt_after": [
            "policies", 
            "supervisor", 
            "client_services",
            "provider_services",
            "general_inquiry",
            "pqrs",
            "new_client",
            "transfer"
        ]
    }
    
    if checkpointer:
        config["checkpoint"] = checkpointer
        
    app = builder.compile(**config)

    return app


def initialize_state() -> GraphState:
    """
    Inicializa el estado general del grafo
    """
    return GraphState(
        messages=[],
        current_state="initial",
        policies_accepted=False,
        greeting_shown=False,
        # Estados de sesión
        client_session=None,  # Almacena info de sesión del cliente
        provider_session=None,  # Almacena info de sesión del proveedor
        active_role=None,  # "client" o "provider"
        # Estados de autenticación
        auth_attempts=0,
        last_auth_time=None,
        # Información de usuario
        user_info=None,
        vehicle_info=None,  # Para clientes
        invoice_info=None,  # Para proveedores
    )
