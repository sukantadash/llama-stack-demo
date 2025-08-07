# inline::meta-reference

## Description

Meta's reference implementation of inference with support for various model formats and optimization techniques.

## Configuration

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `model` | `str \| None` | No |  |  |
| `torch_seed` | `int \| None` | No |  |  |
| `max_seq_len` | `<class 'int'>` | No | 4096 |  |
| `max_batch_size` | `<class 'int'>` | No | 1 |  |
| `model_parallel_size` | `int \| None` | No |  |  |
| `create_distributed_process_group` | `<class 'bool'>` | No | True |  |
| `checkpoint_dir` | `str \| None` | No |  |  |
| `quantization` | `Bf16QuantizationConfig \| Fp8QuantizationConfig \| Int4QuantizationConfig, annotation=NoneType, required=True, discriminator='type'` | No |  |  |

## Sample Configuration

```yaml
model: Llama3.2-3B-Instruct
checkpoint_dir: ${env.CHECKPOINT_DIR:=null}
quantization:
  type: ${env.QUANTIZATION_TYPE:=bf16}
model_parallel_size: ${env.MODEL_PARALLEL_SIZE:=0}
max_batch_size: ${env.MAX_BATCH_SIZE:=1}
max_seq_len: ${env.MAX_SEQ_LEN:=4096}

```

