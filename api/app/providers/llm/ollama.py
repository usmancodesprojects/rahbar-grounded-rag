"""Local Ollama generation using its JSON-schema format."""
import httpx

from ...config import Settings
from ...routes.metrics import TOKENS
from ...schemas import Answer, Passage
from .prompt import messages


class OllamaProvider:
    name = "ollama"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def generate(self, question: str, passages: list[Passage]) -> Answer:
        response = httpx.post(f"{self.settings.ollama_url.rstrip('/')}/api/chat",
                              json={"model": self.settings.llm_model, "stream": False,
                                    "format": Answer.model_json_schema(),
                                    "options": {"temperature": self.settings.temperature,
                                                "num_predict": 750},
                                    "messages": messages(question, passages)},
                              timeout=httpx.Timeout(55, connect=5))
        response.raise_for_status()
        data = response.json()
        TOKENS.labels("input").observe(data.get("prompt_eval_count", 0))
        TOKENS.labels("output").observe(data.get("eval_count", 0))
        return Answer.model_validate_json(data["message"]["content"], strict=True)
