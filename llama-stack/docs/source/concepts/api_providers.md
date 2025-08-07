## API Providers

The goal of Llama Stack is to build an ecosystem where users can easily swap out different implementations for the same API. Examples for these include:
- LLM inference providers (e.g., Fireworks, Together, AWS Bedrock, Groq, Cerebras, SambaNova, vLLM, etc.),
- Vector databases (e.g., ChromaDB, Weaviate, Qdrant, Milvus, FAISS, PGVector, etc.),
- Safety providers (e.g., Meta's Llama Guard, AWS Bedrock Guardrails, etc.)

Providers come in two flavors:
- **Remote**: the provider runs as a separate service external to the Llama Stack codebase. Llama Stack contains a small amount of adapter code.
- **Inline**: the provider is fully specified and implemented within the Llama Stack codebase. It may be a simple wrapper around an existing library, or a full fledged implementation within Llama Stack.

Most importantly, Llama Stack always strives to provide at least one fully inline provider for each API so you can iterate on a fully featured environment locally.
