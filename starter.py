from contextlib import asynccontextmanager
from uuid import uuid4

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from langfuse import observe
from temporalio.client import Client

from opentelemetry_interceptor import OpenTelemetryContextPropagationInterceptor
from workflow import LangChainWorkflow, TranslateWorkflowParams

# Load environment variables
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.temporal_client = await Client.connect(
        "localhost:7233", interceptors=[OpenTelemetryContextPropagationInterceptor()]
    )
    yield


app = FastAPI(lifespan=lifespan)


@app.post("/translate")
@observe(name="temporal-translation-workflow")
async def translate(phrase: str, language1: str, language2: str, language3: str):
    languages = [language1, language2, language3]
    client = app.state.temporal_client
    
    try:
        result = await client.execute_workflow(
            LangChainWorkflow.run,
            TranslateWorkflowParams(phrase, languages),
            id=f"langchain-translation-{uuid4()}",
            task_queue="langchain-task-queue",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"translations": result}


if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8000)
