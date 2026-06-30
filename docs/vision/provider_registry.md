# Provider Registry Design

Currently, the `Executor` instantiates image providers using an if/else chain inside `_resolve_image_provider()`:

```python
# Current interim approach
if provider_name == "mock":
    return MockProvider()
elif provider_name == "flux":
    return FluxProvider()
```

To support future extensibility without modifying the `Executor`, we will introduce a centralized **Provider Registry** in a future sprint.

## Conceptual Architecture

```mermaid
flowchart TD
    Executor["Executor"] -->|"Query Registry"| Reg["Provider Registry"]
    Reg -->|"Instantiate / Retrieve"| Provider["BaseImageProvider"]
    
    subgraph Registry Mapping
        M1["mock -> MockProvider"]
        M2["flux -> FluxProvider"]
        M3["runpod -> RunPodProvider"]
        M4["comfyui -> ComfyUIProvider"]
    end
    
    Reg -.-> Registry Mapping
```

### The Registry Implementation
The registry acts as a decorator-based or manual registry keeping track of available providers:

```python
# worker/image_providers/registry.py
from typing import Dict, Type
from .base import BaseImageProvider

class ProviderRegistry:
    _providers: Dict[str, Type[BaseImageProvider]] = {}

    @classmethod
    def register(cls, name: str):
        """Decorator to register a provider class."""
        def decorator(subclass: Type[BaseImageProvider]):
            cls._providers[name.lower()] = subclass
            return subclass
        return decorator

    @classmethod
    def get(cls, name: str) -> BaseImageProvider:
        """Resolve and instantiate a provider instance."""
        provider_class = cls._providers.get(name.lower())
        if not provider_class:
            raise ValueError(f"Provider '{name}' not found in registry")
        return provider_class()
```

### Clean Provider Onboarding
Adding a new provider (e.g., `RunPodProvider`) will require zero changes to the `Executor` class:

```python
# worker/image_providers/runpod_provider.py
from .base import BaseImageProvider
from .registry import ProviderRegistry

@ProviderRegistry.register("runpod")
class RunPodProvider(BaseImageProvider):
    def get_name(self) -> str:
        return "runpod"
        
    def generate(self, job: GenerationJob) -> Image.Image:
        # Implementation...
```

The `Executor` will simply call:
```python
# worker/execution/executor.py
from worker.image_providers.registry import ProviderRegistry

class Executor:
    def __init__(self) -> None:
        self.image_provider = ProviderRegistry.get(settings.image_provider)
```
This preserves the SOLID open-closed principle: the `Executor` is open for extension but closed for modification.
