# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.

from enum import Enum, StrEnum
from typing import Annotated, Any, Literal, Protocol

from pydantic import BaseModel, Field, field_validator
from typing_extensions import runtime_checkable

from llama_stack.apis.common.content_types import URL, InterleavedContent
from llama_stack.providers.utils.telemetry.trace_protocol import trace_protocol
from llama_stack.schema_utils import json_schema_type, register_schema, webmethod


@json_schema_type
class RRFRanker(BaseModel):
    """
    Reciprocal Rank Fusion (RRF) ranker configuration.

    :param type: The type of ranker, always "rrf"
    :param impact_factor: The impact factor for RRF scoring. Higher values give more weight to higher-ranked results.
                         Must be greater than 0. Default of 60 is from the original RRF paper (Cormack et al., 2009).
    """

    type: Literal["rrf"] = "rrf"
    impact_factor: float = Field(default=60.0, gt=0.0)  # default of 60 for optimal performance


@json_schema_type
class WeightedRanker(BaseModel):
    """
    Weighted ranker configuration that combines vector and keyword scores.

    :param type: The type of ranker, always "weighted"
    :param alpha: Weight factor between 0 and 1.
                 0 means only use keyword scores,
                 1 means only use vector scores,
                 values in between blend both scores.
    """

    type: Literal["weighted"] = "weighted"
    alpha: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Weight factor between 0 and 1. 0 means only keyword scores, 1 means only vector scores.",
    )


Ranker = Annotated[
    RRFRanker | WeightedRanker,
    Field(discriminator="type"),
]
register_schema(Ranker, name="Ranker")


@json_schema_type
class RAGDocument(BaseModel):
    """
    A document to be used for document ingestion in the RAG Tool.

    :param document_id: The unique identifier for the document.
    :param content: The content of the document.
    :param mime_type: The MIME type of the document.
    :param metadata: Additional metadata for the document.
    """

    document_id: str
    content: InterleavedContent | URL
    mime_type: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


@json_schema_type
class RAGQueryResult(BaseModel):
    content: InterleavedContent | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


@json_schema_type
class RAGQueryGenerator(Enum):
    default = "default"
    llm = "llm"
    custom = "custom"


@json_schema_type
class RAGSearchMode(StrEnum):
    """
    Search modes for RAG query retrieval:
    - VECTOR: Uses vector similarity search for semantic matching
    - KEYWORD: Uses keyword-based search for exact matching
    - HYBRID: Combines both vector and keyword search for better results
    """

    VECTOR = "vector"
    KEYWORD = "keyword"
    HYBRID = "hybrid"


@json_schema_type
class DefaultRAGQueryGeneratorConfig(BaseModel):
    type: Literal["default"] = "default"
    separator: str = " "


@json_schema_type
class LLMRAGQueryGeneratorConfig(BaseModel):
    type: Literal["llm"] = "llm"
    model: str
    template: str


RAGQueryGeneratorConfig = Annotated[
    DefaultRAGQueryGeneratorConfig | LLMRAGQueryGeneratorConfig,
    Field(discriminator="type"),
]
register_schema(RAGQueryGeneratorConfig, name="RAGQueryGeneratorConfig")


@json_schema_type
class RAGQueryConfig(BaseModel):
    """
    Configuration for the RAG query generation.

    :param query_generator_config: Configuration for the query generator.
    :param max_tokens_in_context: Maximum number of tokens in the context.
    :param max_chunks: Maximum number of chunks to retrieve.
    :param chunk_template: Template for formatting each retrieved chunk in the context.
        Available placeholders: {index} (1-based chunk ordinal), {chunk.content} (chunk content string), {metadata} (chunk metadata dict).
        Default: "Result {index}\\nContent: {chunk.content}\\nMetadata: {metadata}\\n"
    :param mode: Search mode for retrieval—either "vector", "keyword", or "hybrid". Default "vector".
    :param ranker: Configuration for the ranker to use in hybrid search. Defaults to RRF ranker.
    """

    # This config defines how a query is generated using the messages
    # for memory bank retrieval.
    query_generator_config: RAGQueryGeneratorConfig = Field(default=DefaultRAGQueryGeneratorConfig())
    max_tokens_in_context: int = 4096
    max_chunks: int = 5
    chunk_template: str = "Result {index}\nContent: {chunk.content}\nMetadata: {metadata}\n"
    mode: RAGSearchMode | None = RAGSearchMode.VECTOR
    ranker: Ranker | None = Field(default=None)  # Only used for hybrid mode

    @field_validator("chunk_template")
    def validate_chunk_template(cls, v: str) -> str:
        if "{chunk.content}" not in v:
            raise ValueError("chunk_template must contain {chunk.content}")
        if "{index}" not in v:
            raise ValueError("chunk_template must contain {index}")
        if len(v) == 0:
            raise ValueError("chunk_template must not be empty")
        return v


@runtime_checkable
@trace_protocol
class RAGToolRuntime(Protocol):
    @webmethod(route="/tool-runtime/rag-tool/insert", method="POST")
    async def insert(
        self,
        documents: list[RAGDocument],
        vector_db_id: str,
        chunk_size_in_tokens: int = 512,
    ) -> None:
        """Index documents so they can be used by the RAG system"""
        ...

    @webmethod(route="/tool-runtime/rag-tool/query", method="POST")
    async def query(
        self,
        content: InterleavedContent,
        vector_db_ids: list[str],
        query_config: RAGQueryConfig | None = None,
    ) -> RAGQueryResult:
        """Query the RAG system for context; typically invoked by the agent"""
        ...
