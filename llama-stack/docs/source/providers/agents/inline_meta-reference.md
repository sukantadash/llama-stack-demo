# inline::meta-reference

## Description

Meta's reference implementation of an agent system that can use tools, access vector databases, and perform complex reasoning tasks.

## Configuration

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `persistence_store` | `utils.kvstore.config.RedisKVStoreConfig \| utils.kvstore.config.SqliteKVStoreConfig \| utils.kvstore.config.PostgresKVStoreConfig \| utils.kvstore.config.MongoDBKVStoreConfig` | No | sqlite |  |
| `responses_store` | `utils.sqlstore.sqlstore.SqliteSqlStoreConfig \| utils.sqlstore.sqlstore.PostgresSqlStoreConfig` | No | sqlite |  |

## Sample Configuration

```yaml
persistence_store:
  type: sqlite
  db_path: ${env.SQLITE_STORE_DIR:=~/.llama/dummy}/agents_store.db
responses_store:
  type: sqlite
  db_path: ${env.SQLITE_STORE_DIR:=~/.llama/dummy}/responses_store.db

```

