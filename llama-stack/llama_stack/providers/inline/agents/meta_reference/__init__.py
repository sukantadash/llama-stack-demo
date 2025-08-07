# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.

from typing import Any

from llama_stack.distribution.datatypes import AccessRule, Api

from .config import MetaReferenceAgentsImplConfig


async def get_provider_impl(config: MetaReferenceAgentsImplConfig, deps: dict[Api, Any], policy: list[AccessRule]):
    from .agents import MetaReferenceAgentsImpl

    impl = MetaReferenceAgentsImpl(
        config,
        deps[Api.inference],
        deps[Api.vector_io],
        deps[Api.safety],
        deps[Api.tool_runtime],
        deps[Api.tool_groups],
        policy,
    )
    await impl.initialize()
    return impl
