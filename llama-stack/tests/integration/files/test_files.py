# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.

from io import BytesIO
from unittest.mock import patch

import pytest
from openai import OpenAI

from llama_stack.distribution.datatypes import User
from llama_stack.distribution.library_client import LlamaStackAsLibraryClient


def test_openai_client_basic_operations(compat_client, client_with_models):
    """Test basic file operations through OpenAI client."""
    if isinstance(client_with_models, LlamaStackAsLibraryClient) and isinstance(compat_client, OpenAI):
        pytest.skip("OpenAI files are not supported when testing with LlamaStackAsLibraryClient")
    client = compat_client

    test_content = b"files test content"

    try:
        # Upload file using OpenAI client
        with BytesIO(test_content) as file_buffer:
            file_buffer.name = "openai_test.txt"
            uploaded_file = client.files.create(file=file_buffer, purpose="assistants")

        # Verify basic response structure
        assert uploaded_file.id.startswith("file-")
        assert hasattr(uploaded_file, "filename")

        # List files
        files_list = client.files.list()
        file_ids = [f.id for f in files_list.data]
        assert uploaded_file.id in file_ids

        # Retrieve file info
        retrieved_file = client.files.retrieve(uploaded_file.id)
        assert retrieved_file.id == uploaded_file.id

        # Retrieve file content - OpenAI client returns httpx Response object
        content_response = client.files.content(uploaded_file.id)
        # The response is an httpx Response object with .content attribute containing bytes
        if isinstance(content_response, str):
            # Llama Stack Client returns a str
            # TODO: fix Llama Stack Client
            content = bytes(content_response, "utf-8")
        else:
            content = content_response.content
        assert content == test_content

        # Delete file
        delete_response = client.files.delete(uploaded_file.id)
        assert delete_response.deleted is True

    except Exception as e:
        # Cleanup in case of failure
        try:
            client.files.delete(uploaded_file.id)
        except Exception:
            pass
        raise e


@patch("llama_stack.providers.utils.sqlstore.authorized_sqlstore.get_authenticated_user")
def test_files_authentication_isolation(mock_get_authenticated_user, compat_client, client_with_models):
    """Test that users can only access their own files."""
    if isinstance(client_with_models, LlamaStackAsLibraryClient) and isinstance(compat_client, OpenAI):
        pytest.skip("OpenAI files are not supported when testing with LlamaStackAsLibraryClient")
    if not isinstance(client_with_models, LlamaStackAsLibraryClient):
        pytest.skip("Authentication tests require LlamaStackAsLibraryClient (library mode)")

    client = compat_client

    # Create two test users
    user1 = User("user1", {"roles": ["user"], "teams": ["team-a"]})
    user2 = User("user2", {"roles": ["user"], "teams": ["team-b"]})

    # User 1 uploads a file
    mock_get_authenticated_user.return_value = user1
    test_content_1 = b"User 1's private file content"

    with BytesIO(test_content_1) as file_buffer:
        file_buffer.name = "user1_file.txt"
        user1_file = client.files.create(file=file_buffer, purpose="assistants")

    # User 2 uploads a file
    mock_get_authenticated_user.return_value = user2
    test_content_2 = b"User 2's private file content"

    with BytesIO(test_content_2) as file_buffer:
        file_buffer.name = "user2_file.txt"
        user2_file = client.files.create(file=file_buffer, purpose="assistants")

    try:
        # User 1 can see their own file
        mock_get_authenticated_user.return_value = user1
        user1_files = client.files.list()
        user1_file_ids = [f.id for f in user1_files.data]
        assert user1_file.id in user1_file_ids
        assert user2_file.id not in user1_file_ids  # Cannot see user2's file

        # User 2 can see their own file
        mock_get_authenticated_user.return_value = user2
        user2_files = client.files.list()
        user2_file_ids = [f.id for f in user2_files.data]
        assert user2_file.id in user2_file_ids
        assert user1_file.id not in user2_file_ids  # Cannot see user1's file

        # User 1 can retrieve their own file
        mock_get_authenticated_user.return_value = user1
        retrieved_file = client.files.retrieve(user1_file.id)
        assert retrieved_file.id == user1_file.id

        # User 1 cannot retrieve user2's file
        mock_get_authenticated_user.return_value = user1
        with pytest.raises(ValueError, match="not found"):
            client.files.retrieve(user2_file.id)

        # User 1 can access their file content
        mock_get_authenticated_user.return_value = user1
        content_response = client.files.content(user1_file.id)
        if isinstance(content_response, str):
            content = bytes(content_response, "utf-8")
        else:
            content = content_response.content
        assert content == test_content_1

        # User 1 cannot access user2's file content
        mock_get_authenticated_user.return_value = user1
        with pytest.raises(ValueError, match="not found"):
            client.files.content(user2_file.id)

        # User 1 can delete their own file
        mock_get_authenticated_user.return_value = user1
        delete_response = client.files.delete(user1_file.id)
        assert delete_response.deleted is True

        # User 1 cannot delete user2's file
        mock_get_authenticated_user.return_value = user1
        with pytest.raises(ValueError, match="not found"):
            client.files.delete(user2_file.id)

        # User 2 can still access their file after user1's file is deleted
        mock_get_authenticated_user.return_value = user2
        retrieved_file = client.files.retrieve(user2_file.id)
        assert retrieved_file.id == user2_file.id

        # Cleanup user2's file
        mock_get_authenticated_user.return_value = user2
        client.files.delete(user2_file.id)

    except Exception as e:
        # Cleanup in case of failure
        try:
            mock_get_authenticated_user.return_value = user1
            client.files.delete(user1_file.id)
        except Exception:
            pass
        try:
            mock_get_authenticated_user.return_value = user2
            client.files.delete(user2_file.id)
        except Exception:
            pass
        raise e


@patch("llama_stack.providers.utils.sqlstore.authorized_sqlstore.get_authenticated_user")
def test_files_authentication_shared_attributes(mock_get_authenticated_user, compat_client, client_with_models):
    """Test access control with users having identical attributes."""
    if isinstance(client_with_models, LlamaStackAsLibraryClient) and isinstance(compat_client, OpenAI):
        pytest.skip("OpenAI files are not supported when testing with LlamaStackAsLibraryClient")
    if not isinstance(client_with_models, LlamaStackAsLibraryClient):
        pytest.skip("Authentication tests require LlamaStackAsLibraryClient (library mode)")

    client = compat_client

    # Create users with identical attributes (required for default policy)
    user_a = User("user-a", {"roles": ["user"], "teams": ["shared-team"]})
    user_b = User("user-b", {"roles": ["user"], "teams": ["shared-team"]})

    # User A uploads a file
    mock_get_authenticated_user.return_value = user_a
    test_content = b"Shared attributes file content"

    with BytesIO(test_content) as file_buffer:
        file_buffer.name = "shared_attributes_file.txt"
        shared_file = client.files.create(file=file_buffer, purpose="assistants")

    try:
        # User B with identical attributes can access the file
        mock_get_authenticated_user.return_value = user_b
        files_list = client.files.list()
        file_ids = [f.id for f in files_list.data]

        # User B should be able to see the file due to identical attributes
        assert shared_file.id in file_ids

        # User B can retrieve file info
        retrieved_file = client.files.retrieve(shared_file.id)
        assert retrieved_file.id == shared_file.id

        # User B can access file content
        content_response = client.files.content(shared_file.id)
        if isinstance(content_response, str):
            content = bytes(content_response, "utf-8")
        else:
            content = content_response.content
        assert content == test_content

        # Cleanup
        mock_get_authenticated_user.return_value = user_a
        client.files.delete(shared_file.id)

    except Exception as e:
        # Cleanup in case of failure
        try:
            mock_get_authenticated_user.return_value = user_a
            client.files.delete(shared_file.id)
        except Exception:
            pass
        try:
            mock_get_authenticated_user.return_value = user_b
            client.files.delete(shared_file.id)
        except Exception:
            pass
        raise e


@patch("llama_stack.providers.utils.sqlstore.authorized_sqlstore.get_authenticated_user")
def test_files_authentication_anonymous_access(mock_get_authenticated_user, compat_client, client_with_models):
    """Test anonymous user behavior when no authentication is present."""
    if isinstance(client_with_models, LlamaStackAsLibraryClient) and isinstance(compat_client, OpenAI):
        pytest.skip("OpenAI files are not supported when testing with LlamaStackAsLibraryClient")
    if not isinstance(client_with_models, LlamaStackAsLibraryClient):
        pytest.skip("Authentication tests require LlamaStackAsLibraryClient (library mode)")

    client = compat_client

    # Simulate anonymous user (no authentication)
    mock_get_authenticated_user.return_value = None

    test_content = b"Anonymous file content"

    with BytesIO(test_content) as file_buffer:
        file_buffer.name = "anonymous_file.txt"
        anonymous_file = client.files.create(file=file_buffer, purpose="assistants")

    try:
        # Anonymous user should be able to access their own uploaded file
        files_list = client.files.list()
        file_ids = [f.id for f in files_list.data]
        assert anonymous_file.id in file_ids

        # Can retrieve file info
        retrieved_file = client.files.retrieve(anonymous_file.id)
        assert retrieved_file.id == anonymous_file.id

        # Can access file content
        content_response = client.files.content(anonymous_file.id)
        if isinstance(content_response, str):
            content = bytes(content_response, "utf-8")
        else:
            content = content_response.content
        assert content == test_content

        # Can delete the file
        delete_response = client.files.delete(anonymous_file.id)
        assert delete_response.deleted is True

    except Exception as e:
        # Cleanup in case of failure
        try:
            client.files.delete(anonymous_file.id)
        except Exception:
            pass
        raise e
