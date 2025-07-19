from dataclasses import dataclass

from langchain.prompts import ChatPromptTemplate
from langchain_anthropic import ChatAnthropic
from langfuse.langchain import CallbackHandler
from temporalio import activity


@dataclass
class TranslateParams:
    phrase: str
    language: str


@activity.defn
async def translate_phrase(params: TranslateParams) -> str:
    # LangChain setup
    template = """You are a helpful assistant who translates between languages.
    Translate the following phrase into the specified language: {phrase}
    Language: {language}"""
    chat_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", template),
            ("human", "Translate"),
        ]
    )
    
    # Initialize Langfuse callback handler
    langfuse_handler = CallbackHandler()
    
    chain = chat_prompt | ChatAnthropic(model="claude-3-7-sonnet-latest")
    # Use the asynchronous invoke method with Langfuse callback
    return (
        dict(
            await chain.ainvoke(
                {"phrase": params.phrase, "language": params.language},
                config={"callbacks": [langfuse_handler]}
            )
        ).get("content")
        or ""
    )
