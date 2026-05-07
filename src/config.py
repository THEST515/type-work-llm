import os
from dataclasses import dataclass, field

DEFAULT_DIAGRAMS = ["class", "activity", "state"]


@dataclass
class Config:
    model_provider: str = "deepseek"
    model_name: str = "deepseek-v4-pro"
    api_base: str = "https://api.deepseek.com"
    api_key: str = ""
    temperature: float = 0.3
    max_tokens: int = 8192
    max_retries: int = 3
    output_format: str = "mermaid"
    output_dir: str = "design"
    diagrams: list[str] = field(default_factory=lambda: DEFAULT_DIAGRAMS.copy())
    verbose: bool = False
    interactive: bool = False

    @classmethod
    def from_yaml(cls, path: str) -> "Config":
        try:
            import yaml
        except ImportError:
            raise ImportError("缺少 pyyaml 库，请运行: pip install pyyaml")
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return cls(
            model_provider=data.get("model_provider", "deepseek"),
            model_name=data.get("model_name", "deepseek-chat"),
            api_base=data.get("api_base", "https://api.deepseek.com"),
            api_key=data.get("api_key", ""),
            temperature=float(data.get("temperature", 0.3)),
            max_tokens=int(data.get("max_tokens", 8192)),
            max_retries=int(data.get("max_retries", 3)),
            output_format=data.get("output_format", "mermaid"),
            output_dir=data.get("output_dir", "design"),
            diagrams=data.get("diagrams", DEFAULT_DIAGRAMS),
            verbose=bool(data.get("verbose", False)),
            interactive=bool(data.get("interactive", False)),
        )

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            model_provider=os.getenv("AGENT_MODEL_PROVIDER", "deepseek"),
            model_name=os.getenv("AGENT_MODEL_NAME", "deepseek-chat"),
            api_base=os.getenv("AGENT_API_BASE", "https://api.deepseek.com"),
            api_key=os.getenv("AGENT_API_KEY", ""),
            temperature=float(os.getenv("AGENT_TEMPERATURE", "0.3")),
            max_tokens=int(os.getenv("AGENT_MAX_TOKENS", "8192")),
            max_retries=int(os.getenv("AGENT_MAX_RETRIES", "3")),
            output_format=os.getenv("AGENT_OUTPUT_FORMAT", "mermaid"),
            output_dir=os.getenv("AGENT_OUTPUT_DIR", "design"),
            diagrams=_parse_diagrams_env(),
            verbose=os.getenv("AGENT_VERBOSE", "").lower() in ("1", "true", "yes"),
            interactive=os.getenv("AGENT_INTERACTIVE", "").lower() in ("1", "true", "yes"),
        )


def _parse_diagrams_env() -> list[str]:
    val = os.getenv("AGENT_DIAGRAMS", "")
    if val:
        return [d.strip() for d in val.split(",")]
    return DEFAULT_DIAGRAMS.copy()
