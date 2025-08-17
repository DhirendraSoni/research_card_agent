import os
from typing import Optional
from langchain_aws import ChatBedrock
from langchain_core.language_models.chat_models import BaseChatModel

def get_bedrock_llm(model_id: Optional[str] = None) -> BaseChatModel:
    """Return a LangChain ChatBedrock client using env vars.
    Requires AWS credentials with Bedrock access and AWS_REGION.
    """
    model = model_id or os.getenv("BEDROCK_MODEL_ID", "amazon.titan-text-express-v1")
    region = os.getenv("AWS_REGION", "us-east-1")
    # ChatBedrock automatically picks up AWS creds from env / config
    llm = ChatBedrock(model_id=model, region_name=region)
    return llm
