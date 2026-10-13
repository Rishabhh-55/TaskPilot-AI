import os

import requests
from dotenv import load_dotenv

load_dotenv()

# Select provider: "lm_studio" locally or "gemini" in the cloud.
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "lm_studio").lower()

if LLM_PROVIDER == "gemini":
    BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai"
    API_KEY = os.getenv("GEMINI_API_KEY", "")
    MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
else:
    BASE_URL = os.getenv(
        "LLM_BASE_URL",
        os.getenv(
            "LM_STUDIO_BASE_URL",
            "http://127.0.0.1:1234/v1",
        ),
    ).rstrip("/")

    API_KEY = os.getenv(
        "LLM_API_KEY",
        os.getenv("LM_STUDIO_API_KEY", "lm-studio"),
    )

    MODEL = os.getenv(
        "LLM_MODEL",
        os.getenv("LM_STUDIO_MODEL", "qwen/qwen3.5-9b"),
    )


class LLMClient:
    def __init__(self, timeout=120):
        self.timeout = timeout
        self.session = requests.Session()

        self.session.headers.update({
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        })

    def chat(self, messages, temperature=0, max_tokens=800):
        if LLM_PROVIDER == "gemini" and not API_KEY:
            raise RuntimeError(
                "GEMINI_API_KEY is missing from the app configuration."
            )

        payload = {
            "model": MODEL,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        try:
            response = self.session.post(
                f"{BASE_URL}/chat/completions",
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()

        except requests.RequestException as exc:
            error_details = ""

            if exc.response is not None:
                error_details = f" | Response: {exc.response.text}"

            raise RuntimeError(
                f"Could not communicate with the configured LLM endpoint: "
                f"{exc}{error_details}"
            ) from exc

        try:
            result = response.json()
            message = result["choices"][0]["message"]

            content = message.get("content")

            if isinstance(content, list):
                content = "".join(
                    item.get("text", "")
                    for item in content
                    if isinstance(item, dict)
                )

            if not content:
                content = message.get("reasoning_content", "")

            if not content:
                raise RuntimeError("The LLM returned an empty response.")

            return content

        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(
                "The LLM endpoint returned an unexpected response."
            ) from exc