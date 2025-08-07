# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.
from collections.abc import Mapping
from typing import Any, Literal

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    inspect,
    select,
    text,
)
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from llama_stack.apis.common.responses import PaginatedResponse
from llama_stack.log import get_logger

from .api import ColumnDefinition, ColumnType, SqlStore
from .sqlstore import SqlAlchemySqlStoreConfig

logger = get_logger(name=__name__, category="sqlstore")

TYPE_MAPPING: dict[ColumnType, Any] = {
    ColumnType.INTEGER: Integer,
    ColumnType.STRING: String,
    ColumnType.FLOAT: Float,
    ColumnType.BOOLEAN: Boolean,
    ColumnType.DATETIME: DateTime,
    ColumnType.TEXT: Text,
    ColumnType.JSON: JSON,
}


class SqlAlchemySqlStoreImpl(SqlStore):
    def __init__(self, config: SqlAlchemySqlStoreConfig):
        self.config = config
        self.async_session = async_sessionmaker(create_async_engine(config.engine_str))
        self.metadata = MetaData()

    async def create_table(
        self,
        table: str,
        schema: Mapping[str, ColumnType | ColumnDefinition],
    ) -> None:
        if not schema:
            raise ValueError(f"No columns defined for table '{table}'.")

        sqlalchemy_columns: list[Column] = []

        for col_name, col_props in schema.items():
            col_type = None
            is_primary_key = False
            is_nullable = True

            if isinstance(col_props, ColumnType):
                col_type = col_props
            elif isinstance(col_props, ColumnDefinition):
                col_type = col_props.type
                is_primary_key = col_props.primary_key
                is_nullable = col_props.nullable

            sqlalchemy_type = TYPE_MAPPING.get(col_type)
            if not sqlalchemy_type:
                raise ValueError(f"Unsupported column type '{col_type}' for column '{col_name}'.")

            sqlalchemy_columns.append(
                Column(col_name, sqlalchemy_type, primary_key=is_primary_key, nullable=is_nullable)
            )

        if table not in self.metadata.tables:
            sqlalchemy_table = Table(table, self.metadata, *sqlalchemy_columns)
        else:
            sqlalchemy_table = self.metadata.tables[table]

        engine = create_async_engine(self.config.engine_str)
        async with engine.begin() as conn:
            await conn.run_sync(self.metadata.create_all, tables=[sqlalchemy_table], checkfirst=True)

    async def insert(self, table: str, data: Mapping[str, Any]) -> None:
        async with self.async_session() as session:
            await session.execute(self.metadata.tables[table].insert(), data)
            await session.commit()

    async def fetch_all(
        self,
        table: str,
        where: Mapping[str, Any] | None = None,
        where_sql: str | None = None,
        limit: int | None = None,
        order_by: list[tuple[str, Literal["asc", "desc"]]] | None = None,
        cursor: tuple[str, str] | None = None,
    ) -> PaginatedResponse:
        async with self.async_session() as session:
            table_obj = self.metadata.tables[table]
            query = select(table_obj)

            if where:
                for key, value in where.items():
                    query = query.where(table_obj.c[key] == value)

            if where_sql:
                query = query.where(text(where_sql))

            # Handle cursor-based pagination
            if cursor:
                # Validate cursor tuple format
                if not isinstance(cursor, tuple) or len(cursor) != 2:
                    raise ValueError(f"Cursor must be a tuple of (key_column, cursor_id), got: {cursor}")

                # Require order_by for cursor pagination
                if not order_by:
                    raise ValueError("order_by is required when using cursor pagination")

                # Only support single-column ordering for cursor pagination
                if len(order_by) != 1:
                    raise ValueError(
                        f"Cursor pagination only supports single-column ordering, got {len(order_by)} columns"
                    )

                cursor_key_column, cursor_id = cursor
                order_column, order_direction = order_by[0]

                # Verify cursor_key_column exists
                if cursor_key_column not in table_obj.c:
                    raise ValueError(f"Cursor key column '{cursor_key_column}' not found in table '{table}'")

                # Get cursor value for the order column
                cursor_query = select(table_obj.c[order_column]).where(table_obj.c[cursor_key_column] == cursor_id)
                cursor_result = await session.execute(cursor_query)
                cursor_row = cursor_result.fetchone()

                if not cursor_row:
                    raise ValueError(f"Record with {cursor_key_column}='{cursor_id}' not found in table '{table}'")

                cursor_value = cursor_row[0]

                # Apply cursor condition based on sort direction
                if order_direction == "desc":
                    query = query.where(table_obj.c[order_column] < cursor_value)
                else:
                    query = query.where(table_obj.c[order_column] > cursor_value)

            # Apply ordering
            if order_by:
                if not isinstance(order_by, list):
                    raise ValueError(
                        f"order_by must be a list of tuples (column, order={['asc', 'desc']}), got {order_by}"
                    )
                for order in order_by:
                    if not isinstance(order, tuple):
                        raise ValueError(
                            f"order_by must be a list of tuples (column, order={['asc', 'desc']}), got {order_by}"
                        )
                    name, order_type = order
                    if name not in table_obj.c:
                        raise ValueError(f"Column '{name}' not found in table '{table}'")
                    if order_type == "asc":
                        query = query.order_by(table_obj.c[name].asc())
                    elif order_type == "desc":
                        query = query.order_by(table_obj.c[name].desc())
                    else:
                        raise ValueError(f"Invalid order '{order_type}' for column '{name}'")

            # Fetch limit + 1 to determine has_more
            fetch_limit = limit
            if limit:
                fetch_limit = limit + 1

            if fetch_limit:
                query = query.limit(fetch_limit)

            result = await session.execute(query)
            if result.rowcount == 0:
                rows = []
            else:
                rows = [dict(row._mapping) for row in result]

            # Always return pagination result
            has_more = False
            if limit and len(rows) > limit:
                has_more = True
                rows = rows[:limit]

            return PaginatedResponse(data=rows, has_more=has_more)

    async def fetch_one(
        self,
        table: str,
        where: Mapping[str, Any] | None = None,
        where_sql: str | None = None,
        order_by: list[tuple[str, Literal["asc", "desc"]]] | None = None,
    ) -> dict[str, Any] | None:
        result = await self.fetch_all(table, where, where_sql, limit=1, order_by=order_by)
        if not result.data:
            return None
        return result.data[0]

    async def update(
        self,
        table: str,
        data: Mapping[str, Any],
        where: Mapping[str, Any],
    ) -> None:
        if not where:
            raise ValueError("where is required for update")

        async with self.async_session() as session:
            stmt = self.metadata.tables[table].update()
            for key, value in where.items():
                stmt = stmt.where(self.metadata.tables[table].c[key] == value)
            await session.execute(stmt, data)
            await session.commit()

    async def delete(self, table: str, where: Mapping[str, Any]) -> None:
        if not where:
            raise ValueError("where is required for delete")

        async with self.async_session() as session:
            stmt = self.metadata.tables[table].delete()
            for key, value in where.items():
                stmt = stmt.where(self.metadata.tables[table].c[key] == value)
            await session.execute(stmt)
            await session.commit()

    async def add_column_if_not_exists(
        self,
        table: str,
        column_name: str,
        column_type: ColumnType,
        nullable: bool = True,
    ) -> None:
        """Add a column to an existing table if the column doesn't already exist."""
        engine = create_async_engine(self.config.engine_str)

        try:
            async with engine.begin() as conn:

                def check_column_exists(sync_conn):
                    inspector = inspect(sync_conn)

                    table_names = inspector.get_table_names()
                    if table not in table_names:
                        return False, False  # table doesn't exist, column doesn't exist

                    existing_columns = inspector.get_columns(table)
                    column_names = [col["name"] for col in existing_columns]

                    return True, column_name in column_names  # table exists, column exists or not

                table_exists, column_exists = await conn.run_sync(check_column_exists)
                if not table_exists or column_exists:
                    return

                sqlalchemy_type = TYPE_MAPPING.get(column_type)
                if not sqlalchemy_type:
                    raise ValueError(f"Unsupported column type '{column_type}' for column '{column_name}'.")

                # Create the ALTER TABLE statement
                # Note: We need to get the dialect-specific type name
                dialect = engine.dialect
                type_impl = sqlalchemy_type()
                compiled_type = type_impl.compile(dialect=dialect)

                nullable_clause = "" if nullable else " NOT NULL"
                add_column_sql = text(f"ALTER TABLE {table} ADD COLUMN {column_name} {compiled_type}{nullable_clause}")

                await conn.execute(add_column_sql)

        except Exception as e:
            # If any error occurs during migration, log it but don't fail
            # The table creation will handle adding the column
            logger.error(f"Error adding column {column_name} to table {table}: {e}")
            pass
