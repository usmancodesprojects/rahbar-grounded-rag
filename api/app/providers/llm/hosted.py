"""Optional OpenAI-compatible endpoint with JSON mode."""
import httpx

from ...config import Settings
from ...routes.metrics import record_tokens
from ...schemas import Answer, Passage
from .prompt import messages


class HostedProvider:
    name = "hosted"

    def __init__(self, settings: Settings) -> None:
        if not settings.hosted_base_url.startswith("https://") or not settings.llm_api_key:
            raise ValueError("hosted generation requires an HTTPS endpoint and a Secret key")
        self.settings = settings

    def generate(self, question: str, passages: list[Passage]) -> Answer:
        prompt = messages(question, passages)
        prompt[0]["content"] += " Output a JSON object using this schema: " + str(
            Answer.model_json_schema()
        )
        response = httpx.post(
            f"{self.settings.hosted_base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {self.settings.llm_api_key}"},
            json={"model": self.settings.llm_model, "messages": prompt,
                  "temperature": self.settings.temperature, "response_format": {"type": "json_object"}},
            timeout=httpx.Timeout(self.settings.llm_timeout, connect=5),
        )
        response.raise_for_status()
        data = response.json()
        usage = data.get("usage") or {}
        record_tokens(usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0))
        return Answer.model_validate_json(data["choices"][0]["message"]["content"], strict=True)
