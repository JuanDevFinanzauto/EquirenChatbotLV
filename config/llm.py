import boto3
from langchain_aws import ChatBedrock
from functools import lru_cache

@lru_cache()
def get_bedrock_llm():
    """
    Retorna una instancia cacheada del LLM de Bedrock.
    El decorador lru_cache asegura que solo se cree una instancia.
    """
    client = boto3.client(service_name="bedrock-runtime", region_name="us-east-1")
    return ChatBedrock(
        model_id="us.anthropic.claude-3-5-haiku-20241022-v1:0",
        client=client,
        model_kwargs={
            'temperature': 0.1,
            'top_p': 0.4
        }
    )

# Instancia global del LLM
llm = get_bedrock_llm()