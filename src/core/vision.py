"""Google Gemini 2.0 Flash integration for vision analysis."""

import base64
import os
from pathlib import Path
from typing import Optional, Union

from google import genai
from google.genai import types


class GeminiClient:
    """Wrapper for Google Gemini API."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is required")

        self.client = genai.Client(api_key=self.api_key)
        # Use gemini-2.5-flash (latest), configurable via env
        self.model_id = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    def analyze_image(
        self,
        image_data: bytes,
        prompt: str,
        mime_type: str = "image/jpeg",
    ) -> str:
        """
        Analyze an image with a text prompt.

        Args:
            image_data: Raw image bytes
            prompt: Text prompt for analysis
            mime_type: Image MIME type (image/jpeg, image/png, etc.)

        Returns:
            Text response from Gemini
        """
        response = self.client.models.generate_content(
            model=self.model_id,
            contents=[
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=prompt),
                        types.Part.from_bytes(data=image_data, mime_type=mime_type),
                    ],
                )
            ],
            config=types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=4096,
            ),
        )

        return response.text

    def analyze_image_from_url(self, image_url: str, prompt: str) -> str:
        """
        Analyze an image from a URL.

        Args:
            image_url: URL of the image
            prompt: Text prompt for analysis

        Returns:
            Text response from Gemini
        """
        import httpx

        response = httpx.get(image_url, timeout=30.0)
        response.raise_for_status()

        content_type = response.headers.get("content-type", "image/jpeg")
        return self.analyze_image(response.content, prompt, mime_type=content_type)

    def analyze_image_from_file(self, file_path: Union[str, Path], prompt: str) -> str:
        """
        Analyze an image from a local file.

        Args:
            file_path: Path to the image file
            prompt: Text prompt for analysis

        Returns:
            Text response from Gemini
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Image file not found: {file_path}")

        mime_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }

        mime_type = mime_types.get(file_path.suffix.lower(), "image/jpeg")
        image_data = file_path.read_bytes()

        return self.analyze_image(image_data, prompt, mime_type=mime_type)

    def analyze_image_from_base64(
        self,
        base64_data: str,
        prompt: str,
        mime_type: str = "image/jpeg",
    ) -> str:
        """
        Analyze an image from base64-encoded data.

        Args:
            base64_data: Base64-encoded image data
            prompt: Text prompt for analysis
            mime_type: Image MIME type

        Returns:
            Text response from Gemini
        """
        # Remove data URL prefix if present
        if "," in base64_data:
            base64_data = base64_data.split(",", 1)[1]

        image_data = base64.b64decode(base64_data)
        return self.analyze_image(image_data, prompt, mime_type=mime_type)


# Singleton instance
_client: Optional[GeminiClient] = None


def get_gemini_client() -> GeminiClient:
    """Get or create the Gemini client singleton."""
    global _client
    if _client is None:
        _client = GeminiClient()
    return _client
