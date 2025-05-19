from typing import Sequence, Union
from langgraph.graph import Graph, MessageGraph
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
import requests
from tools.api_tools.loguer import validate_cliente_api, validate_proveedor_api
from tools.api_tools.auth_token import get_auth_token_api
from graph.states.login_state import LoginState
from config.llm import llm  # Importing centralized LLM


# Constants
MAX_RETRIES = 3

# Document Extraction Schema
class UserDocument(BaseModel):
    document: Union[int, None] = Field(None, description="Documento de identidad sin puntos ni espacios")

def create_login_graph():
    # Document Collector Node
    def document_collector(
        state: LoginState,
        messages: Sequence[BaseMessage]
    ) -> dict:
        human_messages = [m for m in messages if isinstance(m, HumanMessage)]
        if not human_messages:
            return {
                "messages": [AIMessage(content="Por favor proporciona tu número de documento.")],
                "should_wait_for_input": True
            }
        
        last_message = human_messages[-1].content
        
        prompt_text = f"""
        Eres un asistente que extrae únicamente el número de documento de identidad (entero, sin puntos ni espacios) del siguiente mensaje:

        Mensaje del usuario: {last_message}

        Devuelve solo el campo 'document' como entero o null si no existe.
        """

        prompt = ChatPromptTemplate.from_template(prompt_text)
        chain = prompt | llm.with_structured_output(UserDocument)
        extracted = chain.invoke({"last_human_message": last_message})

        return {
            "user_doc": extracted.document,
            "has_document": bool(extracted.document)
        }

    # Document Verifier Node
    def document_verifier(state: LoginState) -> dict:
        if not state.get("user_doc"):
            return {
                "document_verified": False,
                "messages": [AIMessage(content="No se encontró documento para verificar.")],
                "should_wait_for_input": True
            }
        
        token = get_auth_token_api()

        try:
            if state["requested_role"] == "cliente":
                response = validate_cliente_api(state["user_doc"], token)
            elif state["requested_role"] == "proveedor":
                response = validate_proveedor_api(state["user_doc"], token)
            else:
                return {
                    "document_verified": False,
                    "messages": [AIMessage(content="Rol desconocido")]
                }

            if response is None:
                return {
                    "document_verified": False,
                    "messages": [AIMessage(content="No se encontró información para el documento proporcionado, inténtelo nuevamente.")],
                    "should_wait_for_input": True
                }

            info_key = "client_info" if state["requested_role"] == "cliente" else "provider_info"
            return {
                "document_verified": True,
                info_key: response,
                "messages": [AIMessage(content="Verificación exitosa")]
            }

        except requests.RequestException as e:
            return {
                "document_verified": False,
                "messages": [AIMessage(content=f"Error al conectar con la API: {str(e)}")],
                "should_wait_for_input": True
            }

    # Retry Handler Node
    def retry_handler(state: LoginState) -> dict:
        reintentos = state.get("reintentos", 0) + 1
        if reintentos >= MAX_RETRIES:
            return {
                "messages": [AIMessage(content="Lo siento, no pudimos validar tu información después de varios intentos. Intenta más tarde.")],
                "finalizar": True
            }

        return {
            "messages": [AIMessage(content="Por favor, proporciona nuevamente tu número de documento.")],
            "reintentos": reintentos,
            "should_wait_for_input": True
        }

    # Graph Construction
    workflow = Graph()

    # Add nodes
    workflow.add_node("collect_document", document_collector)
    workflow.add_node("verify_document", document_verifier)
    workflow.add_node("retry_handler", retry_handler)

    # Define edges with conditions
    workflow.add_conditional_edges(
        "collect_document",
        lambda state: "verify_document" if state.get("has_document", False) else "retry_handler"
    )
    
    workflow.add_conditional_edges(
        "verify_document",
        lambda state: "end" if state.get("document_verified", False) else "retry_handler"
    )
    
    workflow.add_conditional_edges(
        "retry_handler",
        lambda state: "end" if state.get("finalizar", False) else "collect_document"
    )

    # Set entry point
    workflow.set_entry_point("collect_document")

    return workflow.compile()

# Create the login agent
login_agent = create_login_graph()

# Function to initialize login state
def initialize_login_state(requested_role=None) -> LoginState:
    """Inicializa el estado para el flujo de login"""
    return LoginState(
        messages=[],
        requested_role=requested_role,
        user_doc=None,
        document_verified=False,
        has_document=False,
        reintentos=0,
        client_info={},
        provider_info={},
        should_wait_for_input=True
    )
