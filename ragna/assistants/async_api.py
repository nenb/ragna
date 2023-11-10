import json
import os

import ragna
from ragna.core import (
    Assistant,
    Config,
    EnvVarRequirement,
    Requirement,
    Source,
    task_config,
)


class StreamOpenaiApiAssistant(Assistant):
    _API_KEY_ENV_VAR = "OPENAI_API_KEY"
    _MODEL: str
    _CONTEXT_SIZE: int

    @classmethod
    def display_name(cls) -> str:
        return f"StreamOpenAI/{cls._MODEL}"

    @property
    def max_input_size(self) -> int:
        return self._CONTEXT_SIZE

    def _make_system_content(self, sources: list[Source]) -> str:
        # See https://github.com/openai/openai-cookbook/blob/main/examples/How_to_format_inputs_to_ChatGPT_models.ipynb
        instruction = (
            "You are an helpful assistants that answers user questions given the context below. "
            "If you don't know the answer, just say so. Don't try to make up an answer. "
            "Only use the sources below to generate the answer."
        )
        return instruction + "\n\n".join(source.content for source in sources)

    _API_KEY_ENV_VAR: str

    @classmethod
    def requirements(cls) -> list[Requirement]:
        return [EnvVarRequirement(cls._API_KEY_ENV_VAR)]

    def __init__(self, config: Config) -> None:
        super().__init__(config)

        import httpx

        self._client = httpx.AsyncClient(
            headers={"User-Agent": f"{ragna.__version__}/{self}"},
            timeout=60,
        )
        self._api_key = os.environ[self._API_KEY_ENV_VAR]

    @task_config(retries=2, retry_delay=1)
    async def answer(
        self, prompt: str, sources: list[Source], *, max_new_tokens: int = 256
    ):
        async with self._client.stream(
            "POST",
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key}",
            },
            json={
                "messages": [
                    {
                        "role": "system",
                        "content": self._make_system_content(sources),
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                "model": self._MODEL,
                "temperature": 0.0,
                "max_tokens": max_new_tokens,
                "stream": True,
            },
        ) as r:
            async for chunk in r.aiter_lines():
                if len(chunk) > 0:
                    chunk = chunk[6:]  # prepended with "data: "
                    if chunk != "[DONE]":
                        chunk_dict = json.loads(chunk)
                        delta = chunk_dict["choices"][0]["delta"].get("content")
                        if delta:
                            yield delta


class StreamGpt35Turbo16k(StreamOpenaiApiAssistant):
    """[OpenAI GPT-3.5](https://platform.openai.com/docs/models/gpt-3-5)

    !!! info "Required environment variables"

        - `OPENAI_API_KEY`
    """

    _MODEL = "gpt-3.5-turbo-16k"
    _CONTEXT_SIZE = 16_384
