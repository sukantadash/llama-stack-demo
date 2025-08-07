# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.

from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, Field, model_validator

from llama_stack.models.llama.datatypes import ToolCall
from llama_stack.schema_utils import json_schema_type, register_schema


@json_schema_type
class URL(BaseModel):
    uri: str


class _URLOrData(BaseModel):
    """
    A URL or a base64 encoded string

    :param url: A URL of the image or data URL in the format of data:image/{type};base64,{data}. Note that URL could have length limits.
    :param data: base64 encoded image data as string
    """

    url: URL | None = None
    # data is a base64 encoded string, hint with contentEncoding=base64
    data: str | None = Field(default=None, json_schema_extra={"contentEncoding": "base64"})

    @model_validator(mode="before")
    @classmethod
    def validator(cls, values):
        if isinstance(values, dict):
            return values
        return {"url": values}


@json_schema_type
class ImageContentItem(BaseModel):
    """A image content item

    :param type: Discriminator type of the content item. Always "image"
    :param image: Image as a base64 encoded string or an URL
    """

    type: Literal["image"] = "image"
    image: _URLOrData


@json_schema_type
class TextContentItem(BaseModel):
    """A text content item

    :param type: Discriminator type of the content item. Always "text"
    :param text: Text content
    """

    type: Literal["text"] = "text"
    text: str


# other modalities can be added here
InterleavedContentItem = Annotated[
    ImageContentItem | TextContentItem,
    Field(discriminator="type"),
]
register_schema(InterleavedContentItem, name="InterleavedContentItem")

# accept a single "str" as a special case since it is common
InterleavedContent = str | InterleavedContentItem | list[InterleavedContentItem]
register_schema(InterleavedContent, name="InterleavedContent")


@json_schema_type
class TextDelta(BaseModel):
    type: Literal["text"] = "text"
    text: str


@json_schema_type
class ImageDelta(BaseModel):
    type: Literal["image"] = "image"
    image: bytes


class ToolCallParseStatus(Enum):
    started = "started"
    in_progress = "in_progress"
    failed = "failed"
    succeeded = "succeeded"


@json_schema_type
class ToolCallDelta(BaseModel):
    type: Literal["tool_call"] = "tool_call"

    # you either send an in-progress tool call so the client can stream a long
    # code generation or you send the final parsed tool call at the end of the
    # stream
    tool_call: str | ToolCall
    parse_status: ToolCallParseStatus


# streaming completions send a stream of ContentDeltas
ContentDelta = Annotated[
    TextDelta | ImageDelta | ToolCallDelta,
    Field(discriminator="type"),
]
register_schema(ContentDelta, name="ContentDelta")
