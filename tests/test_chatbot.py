from typing import List
from langchain_core.messages import HumanMessage, AIMessage
from graph.builder import build_graph, initialize_state

def print_messages(messages: List[AIMessage | HumanMessage]) -> None:
    """Imprime los mensajes de la conversación de forma legible"""
    for message in messages:
        prefix = "🤖 Bot:" if isinstance(message, AIMessage) else "👤 Usuario:"
        print(f"{prefix} {message.content}")
    print("-" * 50)

def simulate_conversation():
    try:
        # Construir el grafo sin checkpoint para pruebas
        graph = build_graph(use_checkpoint=False)
        
        # Inicializar el estado
        state = initialize_state()
        
        # Simular la conversación
        print("\n🤖 Iniciando conversación...\n")
        
        # Primera interacción - Mensaje inicial
        result = graph.invoke(state)
        print_messages(result["messages"])
        
        # Simular respuesta: Cliente
        state = result
        state["messages"].append(HumanMessage(content="Si, acepto las políticas. Soy cliente."))
        result = graph.invoke(state)
        print_messages(result["messages"])
        
        # Simular documento válido
        state = result
        state["messages"].append(HumanMessage(content="Mi documento es 12345678"))
        result = graph.invoke(state)
        print_messages(result["messages"])
        
        # Verificar el estado final
        print("\n📊 Estado final:")
        print(f"Rol solicitado: {result.get('requested_role')}")
        print(f"Documento verificado: {result.get('document_verified')}")
        print(f"Documento: {result.get('user_doc')}")
        
    except Exception as e:
        print(f"Error durante la simulación: {e}")

if __name__ == "__main__":
    simulate_conversation()
