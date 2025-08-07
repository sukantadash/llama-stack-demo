# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.

from unittest.mock import AsyncMock, MagicMock

import pytest

from llama_stack.apis.tools.rag_tool import RAGQueryConfig
from llama_stack.apis.vector_io import (
    Chunk,
    ChunkMetadata,
    QueryChunksResponse,
)
from llama_stack.providers.inline.tool_runtime.rag.memory import MemoryToolRuntimeImpl


class TestRagQuery:
    async def test_query_raises_on_empty_vector_db_ids(self):
        rag_tool = MemoryToolRuntimeImpl(config=MagicMock(), vector_io_api=MagicMock(), inference_api=MagicMock())
        with pytest.raises(ValueError):
            await rag_tool.query(content=MagicMock(), vector_db_ids=[])

    async def test_query_chunk_metadata_handling(self):
        rag_tool = MemoryToolRuntimeImpl(config=MagicMock(), vector_io_api=MagicMock(), inference_api=MagicMock())
        content = "test query content"
        vector_db_ids = ["db1"]

        chunk_metadata = ChunkMetadata(
            document_id="doc1",
            chunk_id="chunk1",
            source="test_source",
            metadata_token_count=5,
        )
        interleaved_content = MagicMock()
        chunk = Chunk(
            content=interleaved_content,
            metadata={
                "key1": "value1",
                "token_count": 10,
                "metadata_token_count": 5,
                # Note this is inserted into `metadata` during MemoryToolRuntimeImpl().insert()
                "document_id": "doc1",
            },
            stored_chunk_id="chunk1",
            chunk_metadata=chunk_metadata,
        )

        query_response = QueryChunksResponse(chunks=[chunk], scores=[1.0])

        rag_tool.vector_io_api.query_chunks = AsyncMock(return_value=query_response)
        result = await rag_tool.query(content=content, vector_db_ids=vector_db_ids)

        assert result is not None
        expected_metadata_string = (
            "Metadata: {'chunk_id': 'chunk1', 'document_id': 'doc1', 'source': 'test_source', 'key1': 'value1'}"
        )
        assert expected_metadata_string in result.content[1].text
        assert result.content is not None

    async def test_query_raises_incorrect_mode(self):
        with pytest.raises(ValueError):
            RAGQueryConfig(mode="invalid_mode")

    async def test_query_accepts_valid_modes(self):
        default_config = RAGQueryConfig()  # Test default (vector)
        assert default_config.mode == "vector"
        vector_config = RAGQueryConfig(mode="vector")  # Test vector
        assert vector_config.mode == "vector"
        keyword_config = RAGQueryConfig(mode="keyword")  # Test keyword
        assert keyword_config.mode == "keyword"
        hybrid_config = RAGQueryConfig(mode="hybrid")  # Test hybrid
        assert hybrid_config.mode == "hybrid"

        # Test that invalid mode raises an error
        with pytest.raises(ValueError):
            RAGQueryConfig(mode="wrong_mode")
