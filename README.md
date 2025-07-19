# LangChain Sample

This sample shows you how you can use Temporal to orchestrate workflows for [LangChain](https://www.langchain.com). It includes an interceptor that makes Langfuse traces work seamlessly across Temporal clients, workflows and activities using OpenTelemetry context propagation.

For this sample, install the dependencies:

    uv sync

Create a .env file in the root directory with the following content:

    ANTHROPIC_API_KEY=YOUR_API_KEY
    LANGFUSE_PUBLIC_KEY=YOUR_LANGFUSE_PUBLIC_KEY
    LANGFUSE_SECRET_KEY=YOUR_LANGFUSE_SECRET_KEY
    LANGFUSE_HOST=http://localhost:3000

[Anthropic API key](https://docs.anthropic.com/en/api/overview)

For Langfuse setup, you can either:
- Use [Langfuse Cloud](https://cloud.langfuse.com) (free tier available)
- Run locally with Docker: `docker-compose up -d` (using the official Langfuse docker-compose.yml)

Requirements

- Python 3.13+
- Temporal Server (temporal server start-dev)
- python uv
- Langfuse (local Docker or cloud)

To run the sample:

1. Start Temporal dev server:
   ```bash
   temporal server start-dev
   ```

2. Start the worker:
   ```bash
   uv run worker.py
   ```

3. Start the API server:
   ```bash
   uv run starter.py
   ```

4. Test the translation endpoint:
   ```bash
   curl -X POST "http://localhost:8000/translate?phrase=hello%20world&language1=Spanish&language2=French&language3=Russian"
   ```

Which should produce output like:

    {"translations":{"French":"Bonjour tout le monde","Russian":"Привет, мир","Spanish":"Hola mundo"}}

Check your Langfuse dashboard (http://localhost:3000 or your cloud instance) for the unified trace showing the complete workflow execution with all LangChain operations nested under a single trace.

