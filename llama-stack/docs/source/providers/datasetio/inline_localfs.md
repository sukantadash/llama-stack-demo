# inline::localfs

## Description

Local filesystem-based dataset I/O provider for reading and writing datasets to local storage.

## Configuration

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `kvstore` | `utils.kvstore.config.RedisKVStoreConfig \| utils.kvstore.config.SqliteKVStoreConfig \| utils.kvstore.config.PostgresKVStoreConfig \| utils.kvstore.config.MongoDBKVStoreConfig` | No | sqlite |  |

## Sample Configuration

```yaml
kvstore:
  type: sqlite
  db_path: ${env.SQLITE_STORE_DIR:=~/.llama/dummy}/localfs_datasetio.db

```

