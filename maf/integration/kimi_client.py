"""Kimi API Client — integrates with Moonshot AI (Kimi) LLM API.

Usage:
    from maf.integration import KimiClient
    
    client = KimiClient.from_config("integrations/kimi.yaml")
    result = client.chat("Summarize the impact of AI on democracy")
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional


class KimiClient:
    """Client for the Kimi (Moonshot AI) LLM API.
    
    Reads API key from KIMI_API_KEY environment variable.
    Never hardcodes credentials.
    """

    def __init__(
        self,
        integration_id: str = "kimi_llm",
        base_url: str = "https://api.moonshot.cn/v1",
        model: str = "kimi-k2-0711",
        timeout: int = 120,
        temperature: float = 0.7,
        max_tokens: int = 8192,
    ) -> None:
        self.integration_id = integration_id
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._api_key = os.environ.get("KIMI_API_KEY")

    def _ensure_api_key(self) -> None:
        """Validate that an API key is configured before making a request."""
        if not self._api_key:
            raise RuntimeError(
                "KIMI_API_KEY environment variable not set. "
                "Set it with: export KIMI_API_KEY=sk-kimi-..."
            )

    @classmethod
    def from_config(cls, config_path: str) -> "KimiClient":
        """Create a Kimi client from a YAML config file."""
        import yaml
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        cfg = config.get("config", {})
        return cls(
            integration_id=config.get("integration_id", "kimi_llm"),
            base_url=cfg.get("url", "https://api.moonshot.cn/v1"),
            model=cfg.get("models", ["kimi-k2-0711"])[0],
            timeout=cfg.get("timeout", 120),
            temperature=cfg.get("temperature", 0.7),
            max_tokens=cfg.get("max_tokens", 8192),
        )

    def chat(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Send a chat completion request and return the response text."""
        import urllib.request

        self._ensure_api_key()

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key}",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
                return data["choices"][0]["message"]["content"]
        except Exception as e:
            return f"[Kimi API Error: {e}]"

    def chat_with_tools(
        self,
        prompt: str,
        tools: Optional[List[Dict[str, Any]]] = None,
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send a chat completion with tool calling support."""
        import urllib.request

        self._ensure_api_key()

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        if tools:
            payload["tools"] = tools

        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key}",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as e:
            return {"error": str(e)}

    def health_check(self) -> Dict[str, Any]:
        """Check if the Kimi API is reachable."""
        if not self._api_key:
            return {"status": "unavailable", "reason": "KIMI_API_KEY not set"}
        try:
            import urllib.request
            req = urllib.request.Request(
                f"{self.base_url}/models",
                headers={"Authorization": f"Bearer {self._api_key}"},
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    return {"status": "healthy", "provider": "kimi"}
                return {"status": "degraded", "code": response.status}
        except Exception as e:
            return {"status": "unavailable", "reason": str(e)}
