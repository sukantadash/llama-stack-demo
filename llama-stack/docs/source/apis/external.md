# External APIs

Llama Stack supports external APIs that live outside of the main codebase. This allows you to:
- Create and maintain your own APIs independently
- Share APIs with others without contributing to the main codebase
- Keep API-specific code separate from the core Llama Stack code

## Configuration

To enable external APIs, you need to configure the `external_apis_dir` in your Llama Stack configuration. This directory should contain your external API specifications:

```yaml
external_apis_dir: ~/.llama/apis.d/
```

## Directory Structure

The external APIs directory should follow this structure:

```
apis.d/
  custom_api1.yaml
  custom_api2.yaml
```

Each YAML file in these directories defines an API specification.

## API Specification

Here's an example of an external API specification for a weather API:

```yaml
module: weather
api_dependencies:
  - inference
protocol: WeatherAPI
name: weather
pip_packages:
  - llama-stack-api-weather
```

### API Specification Fields

- `module`: Python module containing the API implementation
- `protocol`: Name of the protocol class for the API
- `name`: Name of the API
- `pip_packages`: List of pip packages to install the API, typically a single package

## Required Implementation

External APIs must expose a `available_providers()` function in their module that returns a list of provider names:

```python
# llama_stack_api_weather/api.py
from llama_stack.providers.datatypes import Api, InlineProviderSpec, ProviderSpec


def available_providers() -> list[ProviderSpec]:
    return [
        InlineProviderSpec(
            api=Api.weather,
            provider_type="inline::darksky",
            pip_packages=[],
            module="llama_stack_provider_darksky",
            config_class="llama_stack_provider_darksky.DarkSkyWeatherImplConfig",
        ),
    ]
```

A Protocol class like so:

```python
# llama_stack_api_weather/api.py
from typing import Protocol

from llama_stack.schema_utils import webmethod


class WeatherAPI(Protocol):
    """
    A protocol for the Weather API.
    """

    @webmethod(route="/locations", method="GET")
    async def get_available_locations() -> dict[str, list[str]]:
        """
        Get the available locations.
        """
        ...
```

## Example: Custom API

Here's a complete example of creating and using a custom API:

1. First, create the API package:

```bash
mkdir -p llama-stack-api-weather
cd llama-stack-api-weather
mkdir src/llama_stack_api_weather
git init
uv init
```

2. Edit `pyproject.toml`:

```toml
[project]
name = "llama-stack-api-weather"
version = "0.1.0"
description = "Weather API for Llama Stack"
readme = "README.md"
requires-python = ">=3.10"
dependencies = ["llama-stack", "pydantic"]

[build-system]
requires = ["setuptools"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["src"]
include = ["llama_stack_api_weather", "llama_stack_api_weather.*"]
```

3. Create the initial files:

```bash
touch src/llama_stack_api_weather/__init__.py
touch src/llama_stack_api_weather/api.py
```

```python
# llama-stack-api-weather/src/llama_stack_api_weather/__init__.py
"""Weather API for Llama Stack."""

from .api import WeatherAPI, available_providers

__all__ = ["WeatherAPI", "available_providers"]
```

4. Create the API implementation:

```python
# llama-stack-api-weather/src/llama_stack_api_weather/weather.py
from typing import Protocol

from llama_stack.providers.datatypes import (
    AdapterSpec,
    Api,
    ProviderSpec,
    RemoteProviderSpec,
)
from llama_stack.schema_utils import webmethod


def available_providers() -> list[ProviderSpec]:
    return [
        RemoteProviderSpec(
            api=Api.weather,
            provider_type="remote::kaze",
            config_class="llama_stack_provider_kaze.KazeProviderConfig",
            adapter=AdapterSpec(
                adapter_type="kaze",
                module="llama_stack_provider_kaze",
                pip_packages=["llama_stack_provider_kaze"],
                config_class="llama_stack_provider_kaze.KazeProviderConfig",
            ),
        ),
    ]


class WeatherProvider(Protocol):
    """
    A protocol for the Weather API.
    """

    @webmethod(route="/weather/locations", method="GET")
    async def get_available_locations() -> dict[str, list[str]]:
        """
        Get the available locations.
        """
        ...
```

5. Create the API specification:

```yaml
# ~/.llama/apis.d/weather.yaml
module: llama_stack_api_weather
name: weather
pip_packages: ["llama-stack-api-weather"]
protocol: WeatherProvider

```

6. Install the API package:

```bash
uv pip install -e .
```

7. Configure Llama Stack to use external APIs:

```yaml
version: "2"
image_name: "llama-stack-api-weather"
apis:
  - weather
providers: {}
external_apis_dir: ~/.llama/apis.d
```

The API will now be available at `/v1/weather/locations`.

## Example: custom provider for the weather API

1. Create the provider package:

```bash
mkdir -p llama-stack-provider-kaze
cd llama-stack-provider-kaze
uv init
```

2. Edit `pyproject.toml`:

```toml
[project]
name = "llama-stack-provider-kaze"
version = "0.1.0"
description = "Kaze weather provider for Llama Stack"
readme = "README.md"
requires-python = ">=3.10"
dependencies = ["llama-stack", "pydantic", "aiohttp"]

[build-system]
requires = ["setuptools"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["src"]
include = ["llama_stack_provider_kaze", "llama_stack_provider_kaze.*"]
```

3. Create the initial files:

```bash
touch src/llama_stack_provider_kaze/__init__.py
touch src/llama_stack_provider_kaze/kaze.py
```

4. Create the provider implementation:


Initialization function:

```python
# llama-stack-provider-kaze/src/llama_stack_provider_kaze/__init__.py
"""Kaze weather provider for Llama Stack."""

from .config import KazeProviderConfig
from .kaze import WeatherKazeAdapter

__all__ = ["KazeProviderConfig", "WeatherKazeAdapter"]


async def get_adapter_impl(config: KazeProviderConfig, _deps):
    from .kaze import WeatherKazeAdapter

    impl = WeatherKazeAdapter(config)
    await impl.initialize()
    return impl
```

Configuration:

```python
# llama-stack-provider-kaze/src/llama_stack_provider_kaze/config.py
from pydantic import BaseModel, Field


class KazeProviderConfig(BaseModel):
    """Configuration for the Kaze weather provider."""

    base_url: str = Field(
        "https://api.kaze.io/v1",
        description="Base URL for the Kaze weather API",
    )
```

Main implementation:

```python
# llama-stack-provider-kaze/src/llama_stack_provider_kaze/kaze.py
from llama_stack_api_weather.api import WeatherProvider

from .config import KazeProviderConfig


class WeatherKazeAdapter(WeatherProvider):
    """Kaze weather provider implementation."""

    def __init__(
        self,
        config: KazeProviderConfig,
    ) -> None:
        self.config = config

    async def initialize(self) -> None:
        pass

    async def get_available_locations(self) -> dict[str, list[str]]:
        """Get available weather locations."""
        return {"locations": ["Paris", "Tokyo"]}
```

5. Create the provider specification:

```yaml
# ~/.llama/providers.d/remote/weather/kaze.yaml
adapter:
  adapter_type: kaze
  pip_packages: ["llama_stack_provider_kaze"]
  config_class: llama_stack_provider_kaze.config.KazeProviderConfig
  module: llama_stack_provider_kaze
optional_api_dependencies: []
```

6. Install the provider package:

```bash
uv pip install -e .
```

7. Configure Llama Stack to use the provider:

```yaml
# ~/.llama/run-byoa.yaml
version: "2"
image_name: "llama-stack-api-weather"
apis:
  - weather
providers:
  weather:
  - provider_id: kaze
    provider_type: remote::kaze
    config: {}
external_apis_dir: ~/.llama/apis.d
external_providers_dir: ~/.llama/providers.d
server:
  port: 8321
```

8. Run the server:

```bash
python -m llama_stack.distribution.server.server --yaml-config ~/.llama/run-byoa.yaml
```

9. Test the API:

```bash
curl -sSf http://127.0.0.1:8321/v1/weather/locations
{"locations":["Paris","Tokyo"]}%
```

## Best Practices

1. **Package Naming**: Use a clear and descriptive name for your API package.

2. **Version Management**: Keep your API package versioned and compatible with the Llama Stack version you're using.

3. **Dependencies**: Only include the minimum required dependencies in your API package.

4. **Documentation**: Include clear documentation in your API package about:
   - Installation requirements
   - Configuration options
   - API endpoints and usage
   - Any limitations or known issues

5. **Testing**: Include tests in your API package to ensure it works correctly with Llama Stack.

## Troubleshooting

If your external API isn't being loaded:

1. Check that the `external_apis_dir` path is correct and accessible.
2. Verify that the YAML files are properly formatted.
3. Ensure all required Python packages are installed.
4. Check the Llama Stack server logs for any error messages - turn on debug logging to get more information using `LLAMA_STACK_LOGGING=all=debug`.
5. Verify that the API package is installed in your Python environment.
