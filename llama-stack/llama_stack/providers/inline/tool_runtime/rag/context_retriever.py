# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.


from jinja2 import Template

from llama_stack.apis.common.content_types import InterleavedContent
from llama_stack.apis.inference import UserMessage
from llama_stack.apis.tools.rag_tool import (
    DefaultRAGQueryGeneratorConfig,
    LLMRAGQueryGeneratorConfig,
    RAGQueryGenerator,
    RAGQueryGeneratorConfig,
)
from llama_stack.providers.utils.inference.prompt_adapter import (
    interleaved_content_as_str,
)


async def generate_rag_query(
    config: RAGQueryGeneratorConfig,
    content: InterleavedContent,
    **kwargs,
):
    """
    Generates a query that will be used for
    retrieving relevant information from the memory bank.
    """
    if config.type == RAGQueryGenerator.default.value:
        query = await default_rag_query_generator(config, content, **kwargs)
    elif config.type == RAGQueryGenerator.llm.value:
        query = await llm_rag_query_generator(config, content, **kwargs)
    else:
        raise NotImplementedError(f"Unsupported memory query generator {config.type}")
    return query


async def default_rag_query_generator(
    config: DefaultRAGQueryGeneratorConfig,
    content: InterleavedContent,
    **kwargs,
):
    return interleaved_content_as_str(content, sep=config.separator)


async def llm_rag_query_generator(
    config: LLMRAGQueryGeneratorConfig,
    content: InterleavedContent,
    **kwargs,
):
    assert "inference_api" in kwargs, "LLMRAGQueryGenerator needs inference_api"
    inference_api = kwargs["inference_api"]

    messages = []
    if isinstance(content, list):
        messages = [interleaved_content_as_str(m) for m in content]
    else:
        messages = [interleaved_content_as_str(content)]

    template = Template(config.template)
    content = template.render({"messages": messages})

    model = config.model
    message = UserMessage(content=content)
    response = await inference_api.chat_completion(
        model_id=model,
        messages=[message],
        stream=False,
    )

    query = response.completion_message.content

    return query
