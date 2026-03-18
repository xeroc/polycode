from typing import Optional

from crewai.llms.providers.openai.completion import OpenAICompletion
from pydantic_settings import BaseSettings, SettingsConfigDict


class GLMSettings(BaseSettings):

    # Celery Configuration
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "glm-5"
    # OPENAI_BASE_URL: str = "https://api.z.ai/api/coding/paas/v4/chat/completions"
    OPENAI_BASE_URL: str = "https://api.z.ai/api/coding/paas/v4"

    model_config = SettingsConfigDict(
        extra="ignore", env_file=".env", case_sensitive=True
    )


settings = GLMSettings()  # pyright:ignore # ty:ignore


class GLMJSONLLM(OpenAICompletion):
    """Custom LLM wrapper for GLM with JSON mode support."""

    def __init__(
        self,
        temperature: Optional[float] = 0.7,
        **kwargs,
    ):
        super().__init__(
            model=settings.OPENAI_MODEL,
            temperature=temperature,
            api_key=settings.OPENAI_API_KEY,  # ty:ignore
            base_url=settings.OPENAI_BASE_URL,  # ty:ignore
            **kwargs,
        )

    # def call(
    #     self,
    #     messages: str | list[LLMMessage],
    #     tools: list[dict[str, BaseTool]] | None = None,
    #     callbacks: list[Any] | None = None,
    #     available_functions: dict[str, Any] | None = None,
    #     from_task: Task | None = None,
    #     from_agent: Agent | None = None,
    #     response_model: type[BaseModel] | None = None,
    # ) -> str | Any:
    #     # Convert string to message format
    #     if isinstance(messages, str):
    #         messages = [{"role": "user", "content": messages}]
    #
    #     # Add system prompt for JSON mode
    #     messages = [
    #         LLMMessage(
    #             role="system",
    #             content="Respond with valid JSON only. Do not include markdown code blocks or explanatory text.",
    #         )
    #     ] + messages
    #
    #     # Prepare request payload
    #     payload = {
    #         "model": self.model,
    #         "messages": messages,
    #         "temperature": self.temperature,
    #     }
    #
    #     # Add response_format for JSON mode
    #     payload["response_format"] = {"type": "json_object"}  # ty:ignore
    #
    #     # Add tools if supported
    #     if tools and self.supports_function_calling():
    #         payload["tools"] = tools
    #
    #     # Make API call
    #     response = requests.post(
    #         str(self.base_url),  # ty:ignore
    #         headers={
    #             "Authorization": f"Bearer {self.api_key}",  # ty:ignore
    #             "Content-Type": "application/json",
    #         },
    #         json=payload,
    #         timeout=60,
    #     )
    #     response.raise_for_status()
    #
    #     result = response.json()
    #     content = result["choices"][0]["message"]["content"]
    #
    #     # Clean markdown fencing if present
    #     if content.startswith("```"):
    #         content = content.split("\n", 1)[1]
    #     if content.startswith("json"):
    #         content = content.split("\n", 1)[1]
    #     if content.endswith("```"):
    #         content = content.rsplit("\n", 1)[0]
    #
    #     return content.strip()

    def supports_function_calling(self) -> bool:
        return True

    def get_context_window_size(self) -> int:
        return 128000  # GLM-4 context window
