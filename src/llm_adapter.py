import os
import time
from src.config import Config


def _resolve_api_key(config: Config) -> str:
    if config.api_key:
        return config.api_key
    env_map = {
        "deepseek": "DEEPSEEK_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
    }
    env_var = env_map.get(config.model_provider, "")
    if env_var:
        return os.getenv(env_var, "")
    return ""


class LLMAdapter:
    """统一的大语言模型调用适配器，支持 DeepSeek、Anthropic、OpenAI。"""

    def __init__(self, config: Config):
        self.config = config
        self.provider = config.model_provider
        self._client = None

    @property
    def client(self):
        if self._client is None:
            api_key = _resolve_api_key(self.config)
            if self.provider == "anthropic":
                import anthropic
                self._client = anthropic.Anthropic(api_key=api_key)
            elif self.provider in ("openai", "deepseek"):
                import openai
                base_url = self.config.api_base
                if self.provider == "deepseek":
                    base_url = base_url or "https://api.deepseek.com"
                self._client = openai.OpenAI(
                    api_key=api_key,
                    base_url=base_url,
                )
            else:
                raise ValueError(f"不支持的模型提供商: {self.provider}")
        return self._client

    def chat(self, prompt: str, system: str = "") -> str:
        last_error = None
        for attempt in range(self.config.max_retries):
            try:
                return self._call_api(prompt, system)
            except Exception as e:
                last_error = e
                if self._is_rate_limit(e):
                    wait = 2 ** attempt
                    if self.config.verbose:
                        print(f"  [速率限制] 等待 {wait}s 后重试")
                    time.sleep(wait)
                elif self._is_retryable(e):
                    if self.config.verbose:
                        print(f"  [调用失败] 重试中")
                    time.sleep(1)
                else:
                    raise
        raise RuntimeError(f"LLM 调用失败，已重试 {self.config.max_retries} 次: {last_error}")

    def _is_rate_limit(self, e: Exception) -> bool:
        msg = str(e).lower()
        return "rate" in msg and ("limit" in msg or "429" in msg)

    def _is_retryable(self, e: Exception) -> bool:
        msg = str(e).lower()
        return any(kw in msg for kw in ["timeout", "server error", "500", "502", "503", "overloaded"])

    def _call_api(self, prompt: str, system: str) -> str:
        if self.provider == "anthropic":
            return self._call_anthropic(prompt, system)
        elif self.provider in ("openai", "deepseek"):
            return self._call_openai(prompt, system)
        else:
            raise ValueError(f"不支持的模型提供商: {self.provider}")

    def _call_anthropic(self, prompt: str, system: str) -> str:
        import anthropic
        try:
            message = self.client.messages.create(
                model=self.config.model_name,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                system=system,
                messages=[{"role": "user", "content": prompt}],
            )
            return message.content[0].text
        except anthropic.APIStatusError as e:
            raise RuntimeError(f"Anthropic API 错误: {e}") from e

    def _call_openai(self, prompt: str, system: str) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        try:
            response = self.client.chat.completions.create(
                model=self.config.model_name,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                messages=messages,
            )
            return response.choices[0].message.content
        except Exception as e:
            raise RuntimeError(f"API 错误: {e}") from e
