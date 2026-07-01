from dataclasses import dataclass

@dataclass
class ProviderRoute:
    model: str
    transport: str  # e.g., 'fal-ai', 'huggingface', 'comfyui', 'mock'
    is_active: bool = True
