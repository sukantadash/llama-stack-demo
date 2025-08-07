# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.

from enum import StrEnum
from typing import Annotated, Literal, Protocol, runtime_checkable

from fastapi import File, Form, Response, UploadFile
from pydantic import BaseModel

from llama_stack.apis.common.responses import Order
from llama_stack.providers.utils.telemetry.trace_protocol import trace_protocol
from llama_stack.schema_utils import json_schema_type, webmethod


# OpenAI Files API Models
class OpenAIFilePurpose(StrEnum):
    """
    Valid purpose values for OpenAI Files API.
    """

    ASSISTANTS = "assistants"
    # TODO: Add other purposes as needed


@json_schema_type
class OpenAIFileObject(BaseModel):
    """
    OpenAI File object as defined in the OpenAI Files API.

    :param object: The object type, which is always "file"
    :param id: The file identifier, which can be referenced in the API endpoints
    :param bytes: The size of the file, in bytes
    :param created_at: The Unix timestamp (in seconds) for when the file was created
    :param expires_at: The Unix timestamp (in seconds) for when the file expires
    :param filename: The name of the file
    :param purpose: The intended purpose of the file
    """

    object: Literal["file"] = "file"
    id: str
    bytes: int
    created_at: int
    expires_at: int
    filename: str
    purpose: OpenAIFilePurpose


@json_schema_type
class ListOpenAIFileResponse(BaseModel):
    """
    Response for listing files in OpenAI Files API.

    :param data: List of file objects
    :param object: The object type, which is always "list"
    """

    data: list[OpenAIFileObject]
    has_more: bool
    first_id: str
    last_id: str
    object: Literal["list"] = "list"


@json_schema_type
class OpenAIFileDeleteResponse(BaseModel):
    """
    Response for deleting a file in OpenAI Files API.

    :param id: The file identifier that was deleted
    :param object: The object type, which is always "file"
    :param deleted: Whether the file was successfully deleted
    """

    id: str
    object: Literal["file"] = "file"
    deleted: bool


@runtime_checkable
@trace_protocol
class Files(Protocol):
    # OpenAI Files API Endpoints
    @webmethod(route="/openai/v1/files", method="POST")
    async def openai_upload_file(
        self,
        file: Annotated[UploadFile, File()],
        purpose: Annotated[OpenAIFilePurpose, Form()],
    ) -> OpenAIFileObject:
        """
        Upload a file that can be used across various endpoints.

        The file upload should be a multipart form request with:
        - file: The File object (not file name) to be uploaded.
        - purpose: The intended purpose of the uploaded file.

        :param file: The uploaded file object containing content and metadata (filename, content_type, etc.).
        :param purpose: The intended purpose of the uploaded file (e.g., "assistants", "fine-tune").
        :returns: An OpenAIFileObject representing the uploaded file.
        """
        ...

    @webmethod(route="/openai/v1/files", method="GET")
    async def openai_list_files(
        self,
        after: str | None = None,
        limit: int | None = 10000,
        order: Order | None = Order.desc,
        purpose: OpenAIFilePurpose | None = None,
    ) -> ListOpenAIFileResponse:
        """
        Returns a list of files that belong to the user's organization.

        :param after: A cursor for use in pagination. `after` is an object ID that defines your place in the list. For instance, if you make a list request and receive 100 objects, ending with obj_foo, your subsequent call can include after=obj_foo in order to fetch the next page of the list.
        :param limit: A limit on the number of objects to be returned. Limit can range between 1 and 10,000, and the default is 10,000.
        :param order: Sort order by the `created_at` timestamp of the objects. `asc` for ascending order and `desc` for descending order.
        :param purpose: Only return files with the given purpose.
        :returns: An ListOpenAIFileResponse containing the list of files.
        """
        ...

    @webmethod(route="/openai/v1/files/{file_id}", method="GET")
    async def openai_retrieve_file(
        self,
        file_id: str,
    ) -> OpenAIFileObject:
        """
        Returns information about a specific file.

        :param file_id: The ID of the file to use for this request.
        :returns: An OpenAIFileObject containing file information.
        """
        ...

    @webmethod(route="/openai/v1/files/{file_id}", method="DELETE")
    async def openai_delete_file(
        self,
        file_id: str,
    ) -> OpenAIFileDeleteResponse:
        """
        Delete a file.

        :param file_id: The ID of the file to use for this request.
        :returns: An OpenAIFileDeleteResponse indicating successful deletion.
        """
        ...

    @webmethod(route="/openai/v1/files/{file_id}/content", method="GET")
    async def openai_retrieve_file_content(
        self,
        file_id: str,
    ) -> Response:
        """
        Returns the contents of the specified file.

        :param file_id: The ID of the file to use for this request.
        :returns: The raw file content as a binary response.
        """
        ...
