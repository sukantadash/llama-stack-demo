# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.

import asyncio
import logging
import re
import sqlite3
import struct
from typing import Any

import numpy as np
import sqlite_vec
from numpy.typing import NDArray

from llama_stack.apis.files import Files
from llama_stack.apis.inference import Inference
from llama_stack.apis.vector_dbs import VectorDB
from llama_stack.apis.vector_io import (
    Chunk,
    QueryChunksResponse,
    VectorIO,
)
from llama_stack.providers.datatypes import VectorDBsProtocolPrivate
from llama_stack.providers.utils.kvstore import kvstore_impl
from llama_stack.providers.utils.kvstore.api import KVStore
from llama_stack.providers.utils.memory.openai_vector_store_mixin import OpenAIVectorStoreMixin
from llama_stack.providers.utils.memory.vector_store import (
    RERANKER_TYPE_RRF,
    RERANKER_TYPE_WEIGHTED,
    EmbeddingIndex,
    VectorDBWithIndex,
)

logger = logging.getLogger(__name__)

# Specifying search mode is dependent on the VectorIO provider.
VECTOR_SEARCH = "vector"
KEYWORD_SEARCH = "keyword"
HYBRID_SEARCH = "hybrid"
SEARCH_MODES = {VECTOR_SEARCH, KEYWORD_SEARCH, HYBRID_SEARCH}

VERSION = "v3"
VECTOR_DBS_PREFIX = f"vector_dbs:sqlite_vec:{VERSION}::"
VECTOR_INDEX_PREFIX = f"vector_index:sqlite_vec:{VERSION}::"
OPENAI_VECTOR_STORES_PREFIX = f"openai_vector_stores:sqlite_vec:{VERSION}::"
OPENAI_VECTOR_STORES_FILES_PREFIX = f"openai_vector_stores_files:sqlite_vec:{VERSION}::"
OPENAI_VECTOR_STORES_FILES_CONTENTS_PREFIX = f"openai_vector_stores_files_contents:sqlite_vec:{VERSION}::"


def serialize_vector(vector: list[float]) -> bytes:
    """Serialize a list of floats into a compact binary representation."""
    return struct.pack(f"{len(vector)}f", *vector)


def _create_sqlite_connection(db_path):
    """Create a SQLite connection with sqlite_vec extension loaded."""
    connection = sqlite3.connect(db_path)
    connection.enable_load_extension(True)
    sqlite_vec.load(connection)
    connection.enable_load_extension(False)
    return connection


def _normalize_scores(scores: dict[str, float]) -> dict[str, float]:
    """Normalize scores to [0,1] range using min-max normalization."""
    if not scores:
        return {}
    min_score = min(scores.values())
    max_score = max(scores.values())
    score_range = max_score - min_score
    if score_range > 0:
        return {doc_id: (score - min_score) / score_range for doc_id, score in scores.items()}
    return dict.fromkeys(scores, 1.0)


def _weighted_rerank(
    vector_scores: dict[str, float],
    keyword_scores: dict[str, float],
    alpha: float = 0.5,
) -> dict[str, float]:
    """ReRanker that uses weighted average of scores."""
    all_ids = set(vector_scores.keys()) | set(keyword_scores.keys())
    normalized_vector_scores = _normalize_scores(vector_scores)
    normalized_keyword_scores = _normalize_scores(keyword_scores)

    return {
        doc_id: (alpha * normalized_keyword_scores.get(doc_id, 0.0))
        + ((1 - alpha) * normalized_vector_scores.get(doc_id, 0.0))
        for doc_id in all_ids
    }


def _rrf_rerank(
    vector_scores: dict[str, float],
    keyword_scores: dict[str, float],
    impact_factor: float = 60.0,
) -> dict[str, float]:
    """ReRanker that uses Reciprocal Rank Fusion."""
    # Convert scores to ranks
    vector_ranks = {
        doc_id: i + 1 for i, (doc_id, _) in enumerate(sorted(vector_scores.items(), key=lambda x: x[1], reverse=True))
    }
    keyword_ranks = {
        doc_id: i + 1 for i, (doc_id, _) in enumerate(sorted(keyword_scores.items(), key=lambda x: x[1], reverse=True))
    }

    all_ids = set(vector_scores.keys()) | set(keyword_scores.keys())
    rrf_scores = {}
    for doc_id in all_ids:
        vector_rank = vector_ranks.get(doc_id, float("inf"))
        keyword_rank = keyword_ranks.get(doc_id, float("inf"))
        # RRF formula: score = 1/(k + r) where k is impact_factor and r is the rank
        rrf_scores[doc_id] = (1.0 / (impact_factor + vector_rank)) + (1.0 / (impact_factor + keyword_rank))
    return rrf_scores


def _make_sql_identifier(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]", "_", name)


class SQLiteVecIndex(EmbeddingIndex):
    """
    An index implementation that stores embeddings in a SQLite virtual table using sqlite-vec.
    Two tables are used:
      - A metadata table (chunks_{bank_id}) that holds the chunk JSON.
      - A virtual table (vec_chunks_{bank_id}) that holds the serialized vector.
      - An FTS5 table (fts_chunks_{bank_id}) for full-text keyword search.
    """

    def __init__(self, dimension: int, db_path: str, bank_id: str, kvstore: KVStore | None = None):
        self.dimension = dimension
        self.db_path = db_path
        self.bank_id = bank_id
        self.metadata_table = _make_sql_identifier(f"chunks_{bank_id}")
        self.vector_table = _make_sql_identifier(f"vec_chunks_{bank_id}")
        self.fts_table = _make_sql_identifier(f"fts_chunks_{bank_id}")
        self.kvstore = kvstore

    @classmethod
    async def create(cls, dimension: int, db_path: str, bank_id: str):
        instance = cls(dimension, db_path, bank_id)
        await instance.initialize()
        return instance

    async def initialize(self) -> None:
        def _init_tables():
            connection = _create_sqlite_connection(self.db_path)
            cur = connection.cursor()
            try:
                # Create the table to store chunk metadata.
                cur.execute(f"""
                    CREATE TABLE IF NOT EXISTS [{self.metadata_table}] (
                        id TEXT PRIMARY KEY,
                        chunk TEXT
                    );
                """)
                # Create the virtual table for embeddings.
                cur.execute(f"""
                    CREATE VIRTUAL TABLE IF NOT EXISTS [{self.vector_table}]
                    USING vec0(embedding FLOAT[{self.dimension}], id TEXT);
                """)
                connection.commit()
                # FTS5 table (for keyword search) - creating both the tables by default. Will use the relevant one
                # based on query. Implementation of the change on client side will allow passing the search_mode option
                # during initialization to make it easier to create the table that is required.
                cur.execute(f"""
                            CREATE VIRTUAL TABLE IF NOT EXISTS [{self.fts_table}]
                            USING fts5(id, content);
                        """)
                connection.commit()
            finally:
                cur.close()
                connection.close()

        await asyncio.to_thread(_init_tables)

    async def delete(self) -> None:
        def _drop_tables():
            connection = _create_sqlite_connection(self.db_path)
            cur = connection.cursor()
            try:
                cur.execute(f"DROP TABLE IF EXISTS [{self.metadata_table}];")
                cur.execute(f"DROP TABLE IF EXISTS [{self.vector_table}];")
                cur.execute(f"DROP TABLE IF EXISTS [{self.fts_table}];")
                connection.commit()
            finally:
                cur.close()
                connection.close()

        await asyncio.to_thread(_drop_tables)

    async def add_chunks(self, chunks: list[Chunk], embeddings: NDArray, batch_size: int = 500):
        """
        Add new chunks along with their embeddings using batch inserts.
        For each chunk, we insert its JSON into the metadata table and then insert its
        embedding (serialized to raw bytes) into the virtual table using the assigned rowid.
        If any insert fails, the transaction is rolled back to maintain consistency.
        Also inserts chunk content into FTS table for keyword search support.
        """
        assert all(isinstance(chunk.content, str) for chunk in chunks), "SQLiteVecIndex only supports text chunks"

        def _execute_all_batch_inserts():
            connection = _create_sqlite_connection(self.db_path)
            cur = connection.cursor()

            try:
                cur.execute("BEGIN TRANSACTION")
                for i in range(0, len(chunks), batch_size):
                    batch_chunks = chunks[i : i + batch_size]
                    batch_embeddings = embeddings[i : i + batch_size]

                    # Insert metadata
                    metadata_data = [(chunk.chunk_id, chunk.model_dump_json()) for chunk in batch_chunks]
                    cur.executemany(
                        f"""
                        INSERT INTO [{self.metadata_table}] (id, chunk)
                        VALUES (?, ?)
                        ON CONFLICT(id) DO UPDATE SET chunk = excluded.chunk;
                        """,
                        metadata_data,
                    )

                    # Insert vector embeddings
                    embedding_data = [
                        (
                            (
                                chunk.chunk_id,
                                serialize_vector(emb.tolist()),
                            )
                        )
                        for chunk, emb in zip(batch_chunks, batch_embeddings, strict=True)
                    ]
                    cur.executemany(
                        f"INSERT INTO [{self.vector_table}] (id, embedding) VALUES (?, ?);",
                        embedding_data,
                    )

                    # Insert FTS content
                    fts_data = [(chunk.chunk_id, chunk.content) for chunk in batch_chunks]
                    # DELETE existing entries with same IDs (FTS5 doesn't support ON CONFLICT)
                    cur.executemany(
                        f"DELETE FROM [{self.fts_table}] WHERE id = ?;",
                        [(row[0],) for row in fts_data],
                    )

                    # INSERT new entries
                    cur.executemany(
                        f"INSERT INTO [{self.fts_table}] (id, content) VALUES (?, ?);",
                        fts_data,
                    )

                connection.commit()

            except sqlite3.Error as e:
                connection.rollback()
                logger.error(f"Error inserting into {self.vector_table}: {e}")
                raise

            finally:
                cur.close()
                connection.close()

        # Run batch insertion in a background thread
        await asyncio.to_thread(_execute_all_batch_inserts)

    async def query_vector(
        self,
        embedding: NDArray,
        k: int,
        score_threshold: float,
    ) -> QueryChunksResponse:
        """
        Performs vector-based search using a virtual table for vector similarity.
        """

        def _execute_query():
            connection = _create_sqlite_connection(self.db_path)
            cur = connection.cursor()
            try:
                emb_list = embedding.tolist() if isinstance(embedding, np.ndarray) else list(embedding)
                emb_blob = serialize_vector(emb_list)
                query_sql = f"""
                    SELECT m.id, m.chunk, v.distance
                    FROM [{self.vector_table}] AS v
                    JOIN [{self.metadata_table}] AS m ON m.id = v.id
                    WHERE v.embedding MATCH ? AND k = ?
                    ORDER BY v.distance;
                """
                cur.execute(query_sql, (emb_blob, k))
                return cur.fetchall()
            finally:
                cur.close()
                connection.close()

        rows = await asyncio.to_thread(_execute_query)
        chunks, scores = [], []
        for row in rows:
            _id, chunk_json, distance = row
            score = 1.0 / distance if distance != 0 else float("inf")
            if score < score_threshold:
                continue
            try:
                chunk = Chunk.model_validate_json(chunk_json)
            except Exception as e:
                logger.error(f"Error parsing chunk JSON for id {_id}: {e}")
                continue
            chunks.append(chunk)
            scores.append(score)
        return QueryChunksResponse(chunks=chunks, scores=scores)

    async def query_keyword(
        self,
        query_string: str,
        k: int,
        score_threshold: float,
    ) -> QueryChunksResponse:
        """
        Performs keyword-based search using SQLite FTS5 for relevance-ranked full-text search.
        """

        def _execute_query():
            connection = _create_sqlite_connection(self.db_path)
            cur = connection.cursor()
            try:
                query_sql = f"""
                    SELECT DISTINCT m.id, m.chunk, bm25([{self.fts_table}]) AS score
                    FROM [{self.fts_table}] AS f
                    JOIN [{self.metadata_table}] AS m ON m.id = f.id
                    WHERE f.content MATCH ?
                    ORDER BY score ASC
                    LIMIT ?;
                """
                cur.execute(query_sql, (query_string, k))
                return cur.fetchall()
            finally:
                cur.close()
                connection.close()

        rows = await asyncio.to_thread(_execute_query)
        chunks, scores = [], []
        for row in rows:
            _id, chunk_json, score = row
            # BM25 scores returned by sqlite-vec are NEGATED (i.e., more relevant = more negative).
            # This design is intentional to simplify sorting by ascending score.
            # Reference: https://alexgarcia.xyz/blog/2024/sqlite-vec-hybrid-search/index.html
            if score > -score_threshold:
                continue
            try:
                chunk = Chunk.model_validate_json(chunk_json)
            except Exception as e:
                logger.error(f"Error parsing chunk JSON for id {_id}: {e}")
                continue
            chunks.append(chunk)
            scores.append(score)
        return QueryChunksResponse(chunks=chunks, scores=scores)

    async def query_hybrid(
        self,
        embedding: NDArray,
        query_string: str,
        k: int,
        score_threshold: float,
        reranker_type: str = RERANKER_TYPE_RRF,
        reranker_params: dict[str, Any] | None = None,
    ) -> QueryChunksResponse:
        """
        Hybrid search using a configurable re-ranking strategy.

        Args:
            embedding: The query embedding vector
            query_string: The text query for keyword search
            k: Number of results to return
            score_threshold: Minimum similarity score threshold
            reranker_type: Type of reranker to use ("rrf" or "weighted")
            reranker_params: Parameters for the reranker

        Returns:
            QueryChunksResponse with combined results
        """
        if reranker_params is None:
            reranker_params = {}

        # Get results from both search methods
        vector_response = await self.query_vector(embedding, k, score_threshold)
        keyword_response = await self.query_keyword(query_string, k, score_threshold)

        # Convert responses to score dictionaries using chunk_id
        vector_scores = {
            chunk.chunk_id: score for chunk, score in zip(vector_response.chunks, vector_response.scores, strict=False)
        }
        keyword_scores = {
            chunk.chunk_id: score
            for chunk, score in zip(keyword_response.chunks, keyword_response.scores, strict=False)
        }

        # Combine scores using the specified reranker
        if reranker_type == RERANKER_TYPE_WEIGHTED:
            alpha = reranker_params.get("alpha", 0.5)
            combined_scores = _weighted_rerank(vector_scores, keyword_scores, alpha)
        else:
            # Default to RRF for None, RRF, or any unknown types
            impact_factor = reranker_params.get("impact_factor", 60.0)
            combined_scores = _rrf_rerank(vector_scores, keyword_scores, impact_factor)

        # Sort by combined score and get top k results
        sorted_items = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)
        top_k_items = sorted_items[:k]

        # Filter by score threshold
        filtered_items = [(doc_id, score) for doc_id, score in top_k_items if score >= score_threshold]

        # Create a map of chunk_id to chunk for both responses
        chunk_map = {c.chunk_id: c for c in vector_response.chunks + keyword_response.chunks}

        # Use the map to look up chunks by their IDs
        chunks = []
        scores = []
        for doc_id, score in filtered_items:
            if doc_id in chunk_map:
                chunks.append(chunk_map[doc_id])
                scores.append(score)

        return QueryChunksResponse(chunks=chunks, scores=scores)

    async def delete_chunk(self, chunk_id: str) -> None:
        """Remove a chunk from the SQLite vector store."""

        def _delete_chunk():
            connection = _create_sqlite_connection(self.db_path)
            cur = connection.cursor()
            try:
                cur.execute("BEGIN TRANSACTION")

                # Delete from metadata table
                cur.execute(f"DELETE FROM {self.metadata_table} WHERE id = ?", (chunk_id,))

                # Delete from vector table
                cur.execute(f"DELETE FROM {self.vector_table} WHERE id = ?", (chunk_id,))

                # Delete from FTS table
                cur.execute(f"DELETE FROM {self.fts_table} WHERE id = ?", (chunk_id,))

                connection.commit()
            except Exception as e:
                connection.rollback()
                logger.error(f"Error deleting chunk {chunk_id}: {e}")
                raise
            finally:
                cur.close()
                connection.close()

        await asyncio.to_thread(_delete_chunk)


class SQLiteVecVectorIOAdapter(OpenAIVectorStoreMixin, VectorIO, VectorDBsProtocolPrivate):
    """
    A VectorIO implementation using SQLite + sqlite_vec.
    This class handles vector database registration (with metadata stored in a table named `vector_dbs`)
    and creates a cache of VectorDBWithIndex instances (each wrapping a SQLiteVecIndex).
    """

    def __init__(self, config, inference_api: Inference, files_api: Files | None) -> None:
        self.config = config
        self.inference_api = inference_api
        self.files_api = files_api
        self.cache: dict[str, VectorDBWithIndex] = {}
        self.openai_vector_stores: dict[str, dict[str, Any]] = {}
        self.kvstore: KVStore | None = None

    async def initialize(self) -> None:
        self.kvstore = await kvstore_impl(self.config.kvstore)

        start_key = VECTOR_DBS_PREFIX
        end_key = f"{VECTOR_DBS_PREFIX}\xff"
        stored_vector_dbs = await self.kvstore.values_in_range(start_key, end_key)
        for db_json in stored_vector_dbs:
            vector_db = VectorDB.model_validate_json(db_json)
            index = await SQLiteVecIndex.create(
                vector_db.embedding_dimension,
                self.config.db_path,
                vector_db.identifier,
            )
            self.cache[vector_db.identifier] = VectorDBWithIndex(vector_db, index, self.inference_api)

        # Load existing OpenAI vector stores into the in-memory cache
        await self.initialize_openai_vector_stores()

    async def shutdown(self) -> None:
        # nothing to do since we don't maintain a persistent connection
        pass

    async def list_vector_dbs(self) -> list[VectorDB]:
        return [v.vector_db for v in self.cache.values()]

    async def register_vector_db(self, vector_db: VectorDB) -> None:
        index = await SQLiteVecIndex.create(
            vector_db.embedding_dimension,
            self.config.db_path,
            vector_db.identifier,
        )
        self.cache[vector_db.identifier] = VectorDBWithIndex(vector_db, index, self.inference_api)

    async def _get_and_cache_vector_db_index(self, vector_db_id: str) -> VectorDBWithIndex | None:
        if vector_db_id in self.cache:
            return self.cache[vector_db_id]

        if self.vector_db_store is None:
            raise ValueError(f"Vector DB {vector_db_id} not found")

        vector_db = self.vector_db_store.get_vector_db(vector_db_id)
        if not vector_db:
            raise ValueError(f"Vector DB {vector_db_id} not found")

        index = VectorDBWithIndex(
            vector_db=vector_db,
            index=SQLiteVecIndex(
                dimension=vector_db.embedding_dimension,
                db_path=self.config.db_path,
                bank_id=vector_db.identifier,
                kvstore=self.kvstore,
            ),
            inference_api=self.inference_api,
        )
        self.cache[vector_db_id] = index
        return index

    async def unregister_vector_db(self, vector_db_id: str) -> None:
        if vector_db_id not in self.cache:
            logger.warning(f"Vector DB {vector_db_id} not found")
            return
        await self.cache[vector_db_id].index.delete()
        del self.cache[vector_db_id]

    async def insert_chunks(self, vector_db_id: str, chunks: list[Chunk], ttl_seconds: int | None = None) -> None:
        index = await self._get_and_cache_vector_db_index(vector_db_id)
        if not index:
            raise ValueError(f"Vector DB {vector_db_id} not found")
        # The VectorDBWithIndex helper is expected to compute embeddings via the inference_api
        # and then call our index's add_chunks.
        await index.insert_chunks(chunks)

    async def query_chunks(
        self, vector_db_id: str, query: Any, params: dict[str, Any] | None = None
    ) -> QueryChunksResponse:
        index = await self._get_and_cache_vector_db_index(vector_db_id)
        if not index:
            raise ValueError(f"Vector DB {vector_db_id} not found")
        return await index.query_chunks(query, params)

    async def delete_chunks(self, store_id: str, chunk_ids: list[str]) -> None:
        """Delete a chunk from a sqlite_vec index."""
        index = await self._get_and_cache_vector_db_index(store_id)
        if not index:
            raise ValueError(f"Vector DB {store_id} not found")

        for chunk_id in chunk_ids:
            # Use the index's delete_chunk method
            await index.index.delete_chunk(chunk_id)
