import os

import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv(
    "LM_STUDIO_BASE_URL",
    "http://127.0.0.1:1234/v1",
).rstrip("/")

API_KEY = os.getenv("LM_STUDIO_API_KEY", "lm-studio")
MODEL = os.getenv("LM_STUDIO_MODEL", "local-model")


class LLMClient:
    def __init__(self, timeout=120):
        self.timeout = timeout
        self.session = requests.Session()

        self.session.headers.update(
            {
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json",
            }
        )

    def chat(self, messages, temperature=0, max_tokens=800):
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
                f"Could not communicate with LM Studio: {exc}"
                f"{error_details}"
            ) from exc

        try:
            result = response.json()
            message = result["choices"][0]["message"]

            # Return the final answer when available.
            content = message.get("content")

            # Fall back to reasoning only if the final answer is empty.
            if not content:
                content = message.get("reasoning_content", "")

            return content

        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(
                "LM Studio returned an unexpected response."
            ) from exc