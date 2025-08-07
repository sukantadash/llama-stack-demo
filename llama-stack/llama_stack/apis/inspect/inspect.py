# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.

from typing import Protocol, runtime_checkable

from pydantic import BaseModel

from llama_stack.providers.datatypes import HealthStatus
from llama_stack.schema_utils import json_schema_type, webmethod


@json_schema_type
class RouteInfo(BaseModel):
    route: str
    method: str
    provider_types: list[str]


@json_schema_type
class HealthInfo(BaseModel):
    status: HealthStatus


@json_schema_type
class VersionInfo(BaseModel):
    version: str


class ListRoutesResponse(BaseModel):
    data: list[RouteInfo]


@runtime_checkable
class Inspect(Protocol):
    @webmethod(route="/inspect/routes", method="GET")
    async def list_routes(self) -> ListRoutesResponse:
        """List all routes.

        :returns: A ListRoutesResponse.
        """
        ...

    @webmethod(route="/health", method="GET")
    async def health(self) -> HealthInfo:
        """Get the health of the service.

        :returns: A HealthInfo.
        """
        ...

    @webmethod(route="/version", method="GET")
    async def version(self) -> VersionInfo:
        """Get the version of the service.

        :returns: A VersionInfo.
        """
        ...
