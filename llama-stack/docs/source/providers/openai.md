## OpenAI API Compatibility

### Server path

Llama Stack exposes an OpenAI-compatible API endpoint at `/v1/openai/v1`. So, for a Llama Stack server running locally on port `8321`, the full url to the OpenAI-compatible API endpoint is `http://localhost:8321/v1/openai/v1`.

### Clients

You should be able to use any client that speaks OpenAI APIs with Llama Stack. We regularly test with the official Llama Stack clients as well as OpenAI's official Python client.

#### Llama Stack Client

When using the Llama Stack client, set the `base_url` to the root of your Llama Stack server. It will automatically route OpenAI-compatible requests to the right server endpoint for you.

```python
from llama_stack_client import LlamaStackClient

client = LlamaStackClient(base_url="http://localhost:8321")
```

#### OpenAI Client

When using an OpenAI client, set the `base_url` to the `/v1/openai/v1` path on your Llama Stack server.

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:8321/v1/openai/v1", api_key="none")
```

Regardless of the client you choose, the following code examples should all work the same.

### APIs implemented

#### Models

Many of the APIs require you to pass in a model parameter. To see the list of models available in your Llama Stack server:

```python
models = client.models.list()
```

#### Responses

:::{note}
The Responses API implementation is still in active development. While it is quite usable, there are still unimplemented parts of the API. We'd love feedback on any use-cases you try that do not work to help prioritize the pieces left to implement. Please open issues in the [meta-llama/llama-stack](https://github.com/meta-llama/llama-stack) GitHub repository with details of anything that does not work.
:::

##### Simple inference

Request:

```
response = client.responses.create(
    model="meta-llama/Llama-3.2-3B-Instruct",
    input="Write a haiku about coding."
)

print(response.output_text)
```
Example output:

```text
Pixels dancing slow
Syntax whispers secrets sweet
Code's gentle silence
```

##### Structured Output

Request:

```python
response = client.responses.create(
    model="meta-llama/Llama-3.2-3B-Instruct",
    input=[
        {
            "role": "system",
            "content": "Extract the participants from the event information.",
        },
        {
            "role": "user",
            "content": "Alice and Bob are going to a science fair on Friday.",
        },
    ],
    text={
        "format": {
            "type": "json_schema",
            "name": "participants",
            "schema": {
                "type": "object",
                "properties": {
                    "participants": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["participants"],
            },
        }
    },
)
print(response.output_text)
```

Example output:

```text
{ "participants": ["Alice", "Bob"] }
```

#### Chat Completions

##### Simple inference

Request:

```python
chat_completion = client.chat.completions.create(
    model="meta-llama/Llama-3.2-3B-Instruct",
    messages=[{"role": "user", "content": "Write a haiku about coding."}],
)

print(chat_completion.choices[0].message.content)
```

Example output:

```text
Lines of code unfold
Logic flows like a river
Code's gentle beauty
```

##### Structured Output

Request:

```python
chat_completion = client.chat.completions.create(
    model="meta-llama/Llama-3.2-3B-Instruct",
    messages=[
        {
            "role": "system",
            "content": "Extract the participants from the event information.",
        },
        {
            "role": "user",
            "content": "Alice and Bob are going to a science fair on Friday.",
        },
    ],
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "participants",
            "schema": {
                "type": "object",
                "properties": {
                    "participants": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["participants"],
            },
        },
    },
)

print(chat_completion.choices[0].message.content)
```

Example output:

```text
{ "participants": ["Alice", "Bob"] }
```

#### Completions

##### Simple inference

Request:

```python
completion = client.completions.create(
    model="meta-llama/Llama-3.2-3B-Instruct", prompt="Write a haiku about coding."
)

print(completion.choices[0].text)
```

Example output:

```text
Lines of code unfurl
Logic whispers in the dark
Art in hidden form
```
