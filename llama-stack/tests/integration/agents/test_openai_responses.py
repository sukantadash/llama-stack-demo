# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.
import pytest
from openai import BadRequestError, OpenAI

from llama_stack.distribution.library_client import LlamaStackAsLibraryClient


@pytest.fixture
def openai_client(client_with_models):
    base_url = f"{client_with_models.base_url}/v1/openai/v1"
    return OpenAI(base_url=base_url, api_key="bar")


@pytest.mark.parametrize(
    "stream",
    [
        True,
        False,
    ],
)
@pytest.mark.parametrize(
    "tools",
    [
        [],
        [
            {
                "type": "function",
                "name": "get_weather",
                "description": "Get the weather in a given city",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "city": {"type": "string", "description": "The city to get the weather for"},
                    },
                },
            }
        ],
    ],
)
def test_responses_store(openai_client, client_with_models, text_model_id, stream, tools):
    if isinstance(client_with_models, LlamaStackAsLibraryClient):
        pytest.skip("OpenAI responses are not supported when testing with library client yet.")

    client = openai_client
    message = "What's the weather in Tokyo?" + (
        " YOU MUST USE THE get_weather function to get the weather." if tools else ""
    )
    response = client.responses.create(
        model=text_model_id,
        input=[
            {
                "role": "user",
                "content": message,
            }
        ],
        stream=stream,
        tools=tools,
    )
    if stream:
        # accumulate the streamed content
        content = ""
        response_id = None
        for chunk in response:
            if response_id is None:
                response_id = chunk.response.id
            if chunk.type == "response.completed":
                response_id = chunk.response.id
                output_type = chunk.response.output[0].type
                if output_type == "message":
                    content = chunk.response.output[0].content[0].text
    else:
        response_id = response.id
        output_type = response.output[0].type
        if output_type == "message":
            content = response.output[0].content[0].text

    # list responses - use the underlying HTTP client for endpoints not in SDK
    list_response = client._client.get("/responses")
    assert list_response.status_code == 200
    data = list_response.json()["data"]
    assert response_id in [r["id"] for r in data]

    # test retrieve response
    retrieved_response = client.responses.retrieve(response_id)
    assert retrieved_response.id == response_id
    assert retrieved_response.model == text_model_id
    assert retrieved_response.output[0].type == output_type, retrieved_response
    if output_type == "message":
        assert retrieved_response.output[0].content[0].text == content

    # Delete the response
    delete_response = client.responses.delete(response_id)
    assert delete_response is None

    with pytest.raises(BadRequestError):
        client.responses.retrieve(response_id)


def test_list_response_input_items(openai_client, client_with_models, text_model_id):
    """Test the new list_openai_response_input_items endpoint."""
    if isinstance(client_with_models, LlamaStackAsLibraryClient):
        pytest.skip("OpenAI responses are not supported when testing with library client yet.")

    client = openai_client
    message = "What is the capital of France?"

    # Create a response first
    response = client.responses.create(
        model=text_model_id,
        input=[
            {
                "role": "user",
                "content": message,
            }
        ],
        stream=False,
    )

    response_id = response.id

    # Test the new list input items endpoint
    input_items_response = client.responses.input_items.list(response_id=response_id)

    # Verify the structure follows OpenAI API spec
    assert input_items_response.object == "list"
    assert hasattr(input_items_response, "data")
    assert isinstance(input_items_response.data, list)
    assert len(input_items_response.data) > 0

    # Verify the input item contains our message
    input_item = input_items_response.data[0]
    assert input_item.type == "message"
    assert input_item.role == "user"
    assert message in str(input_item.content)


def test_list_response_input_items_with_limit_and_order(openai_client, client_with_models, text_model_id):
    """Test the list input items endpoint with limit and order parameters."""
    if isinstance(client_with_models, LlamaStackAsLibraryClient):
        pytest.skip("OpenAI responses are not supported when testing with library client yet.")

    client = openai_client

    # Create a response with multiple input messages to test limit and order
    # Use distinctive content to make order verification more reliable
    messages = [
        {"role": "user", "content": "Message A: What is the capital of France?"},
        {"role": "assistant", "content": "The capital of France is Paris."},
        {"role": "user", "content": "Message B: What about Spain?"},
        {"role": "assistant", "content": "The capital of Spain is Madrid."},
        {"role": "user", "content": "Message C: And Italy?"},
    ]

    response = client.responses.create(
        model=text_model_id,
        input=messages,
        stream=False,
    )

    response_id = response.id

    # First get all items to establish baseline
    all_items_response = client.responses.input_items.list(response_id=response_id)
    assert all_items_response.object == "list"
    total_items = len(all_items_response.data)
    assert total_items == 5  # Should have all 5 input messages

    # Test 1: Limit parameter - request only 2 items
    limited_response = client.responses.input_items.list(response_id=response_id, limit=2)
    assert limited_response.object == "list"
    assert len(limited_response.data) == min(2, total_items)  # Should be exactly 2 or total if less

    # Test 2: Edge case - limit larger than available items
    large_limit_response = client.responses.input_items.list(response_id=response_id, limit=10)
    assert large_limit_response.object == "list"
    assert len(large_limit_response.data) == total_items  # Should return all available items

    # Test 3: Edge case - limit of 1
    single_item_response = client.responses.input_items.list(response_id=response_id, limit=1)
    assert single_item_response.object == "list"
    assert len(single_item_response.data) == 1

    # Test 4: Order parameter - ascending vs descending
    asc_response = client.responses.input_items.list(response_id=response_id, order="asc")
    desc_response = client.responses.input_items.list(response_id=response_id, order="desc")

    assert asc_response.object == "list"
    assert desc_response.object == "list"
    assert len(asc_response.data) == len(desc_response.data) == total_items

    # Verify order is actually different (if we have multiple items)
    if total_items > 1:
        # First item in asc should be last item in desc (reversed order)
        first_asc_content = str(asc_response.data[0].content)
        first_desc_content = str(desc_response.data[0].content)
        last_asc_content = str(asc_response.data[-1].content)
        last_desc_content = str(desc_response.data[-1].content)

        # The first item in asc should be the last item in desc (and vice versa)
        assert first_asc_content == last_desc_content, (
            f"Expected first asc ({first_asc_content}) to equal last desc ({last_desc_content})"
        )
        assert last_asc_content == first_desc_content, (
            f"Expected last asc ({last_asc_content}) to equal first desc ({first_desc_content})"
        )

        # Verify the distinctive content markers are in the right positions
        assert "Message A" in first_asc_content, "First item in ascending order should contain 'Message A'"
        assert "Message C" in first_desc_content, "First item in descending order should contain 'Message C'"

    # Test 5: Combined limit and order
    combined_response = client.responses.input_items.list(response_id=response_id, limit=3, order="desc")
    assert combined_response.object == "list"
    assert len(combined_response.data) == min(3, total_items)

    # Test 6: Verify combined response has correct order for first few items
    if total_items >= 3:
        # Should get the last 3 items in descending order (most recent first)
        assert "Message C" in str(combined_response.data[0].content), "First item should be most recent (Message C)"
        # The exact second and third items depend on the implementation, but let's verify structure
        for item in combined_response.data:
            assert hasattr(item, "content")
            assert hasattr(item, "role")
            assert hasattr(item, "type")
            assert item.type == "message"
            assert item.role in ["user", "assistant"]


@pytest.mark.skip(reason="Tool calling is not reliable.")
def test_function_call_output_response(openai_client, client_with_models, text_model_id):
    """Test handling of function call outputs in responses."""
    if isinstance(client_with_models, LlamaStackAsLibraryClient):
        pytest.skip("OpenAI responses are not supported when testing with library client yet.")

    client = openai_client

    # First create a response that triggers a function call
    response = client.responses.create(
        model=text_model_id,
        input=[
            {
                "role": "user",
                "content": "what's the weather in tokyo? You MUST call the `get_weather` function to find out.",
            }
        ],
        tools=[
            {
                "type": "function",
                "name": "get_weather",
                "description": "Get the weather in a given city",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "city": {"type": "string", "description": "The city to get the weather for"},
                    },
                },
            }
        ],
        stream=False,
    )

    # Verify we got a function call
    assert response.output[0].type == "function_call"
    call_id = response.output[0].call_id

    # Now send the function call output as a follow-up
    response2 = client.responses.create(
        model=text_model_id,
        input=[{"type": "function_call_output", "call_id": call_id, "output": "sunny and warm"}],
        previous_response_id=response.id,
        stream=False,
    )

    # Verify the second response processed successfully
    assert response2.id is not None
    assert response2.output[0].type == "message"
    assert (
        "sunny" in response2.output[0].content[0].text.lower() or "warm" in response2.output[0].content[0].text.lower()
    )
