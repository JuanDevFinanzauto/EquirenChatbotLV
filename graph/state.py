from typing import TypedDict, Optional, Dict, Any, Literal, TypeVar, Callable, AnyStr
from typing_extensions import Annotated
from langgraph.graph.message import AnyMessage, add_messages


class GraphState(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], add_messages]    
    user_doc: Optional[str]
    has_document: Optional[bool]
    document_verified: Optional[bool]
    verification_error: Optional[str]
    requested_role: Optional[str]