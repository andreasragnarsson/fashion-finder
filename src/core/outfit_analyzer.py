"""Multi-item outfit identification from images using Gemini AI."""

import json
import re
from typing import Optional

from pydantic import BaseModel, Field

from .vision import GeminiClient, get_gemini_client


class IdentifiedItem(BaseModel):
    """A single identified clothing item."""

    item_type: str = Field(description="Category like jacket, pants, shoes, etc.")
    description: str = Field(description="Detailed description of the item")
    brand_guess: Optional[str] = Field(default=None, description="Best guess at the brand")
    color: str = Field(description="Primary color(s)")
    pattern: Optional[str] = Field(default=None, description="Pattern like solid, striped, plaid")
    material_guess: Optional[str] = Field(default=None, description="Guessed material")
    style_tags: list[str] = Field(default_factory=list, description="Style descriptors")
    confidence: float = Field(default=0.8, description="Confidence score 0-1")
    search_keywords: list[str] = Field(default_factory=list, description="Keywords for searching")


class OutfitAnalysis(BaseModel):
    """Complete analysis of an outfit from an image."""

    items: list[IdentifiedItem] = Field(default_factory=list)
    overall_style: str = Field(default="", description="Overall style description")
    occasion: Optional[str] = Field(default=None, description="Suggested occasion")
    season: Optional[str] = Field(default=None, description="Suggested season")
    gender: Optional[str] = Field(default=None, description="Apparent gender target")
    age_group: Optional[str] = Field(default=None, description="Apparent age group")
    raw_response: Optional[str] = Field(default=None, description="Raw AI response")


OUTFIT_ANALYSIS_PROMPT = """Analyze this fashion image and identify all visible clothing items and accessories.

For EACH item, provide:
1. item_type: Category (jacket, coat, blazer, shirt, t-shirt, sweater, hoodie, pants, jeans, shorts, skirt, dress, shoes, sneakers, boots, bag, hat, scarf, watch, jewelry, belt, sunglasses, etc.)
2. description: Detailed description (e.g., "Oversized beige wool coat with notch lapels")
3. brand_guess: Your best guess at the brand based on style, logos, or distinctive features (null if unsure)
4. color: Primary color(s) (e.g., "navy blue", "cream/beige")
5. pattern: Pattern type (solid, striped, plaid, floral, graphic, etc.)
6. material_guess: Likely material (cotton, wool, leather, denim, etc.)
7. style_tags: List of style descriptors (e.g., ["minimalist", "scandinavian", "oversized", "casual"])
8. confidence: Your confidence in the identification (0.0-1.0)
9. search_keywords: 3-5 keywords that would help find this item online

Also provide:
- overall_style: The overall aesthetic (e.g., "Scandinavian minimalist", "streetwear", "business casual")
- occasion: Suggested occasion (casual, work, formal, date night, etc.)
- season: Best season for this outfit (spring, summer, fall, winter, all-season)
- gender: Target gender (men, women, unisex)
- age_group: Target age group (kids, teens, young adults, adults)

Return your response as valid JSON matching this structure:
{
    "items": [
        {
            "item_type": "...",
            "description": "...",
            "brand_guess": "...",
            "color": "...",
            "pattern": "...",
            "material_guess": "...",
            "style_tags": ["..."],
            "confidence": 0.9,
            "search_keywords": ["..."]
        }
    ],
    "overall_style": "...",
    "occasion": "...",
    "season": "...",
    "gender": "...",
    "age_group": "..."
}

IMPORTANT - BRAND IDENTIFICATION IS CRITICAL:
- ALWAYS try to identify the SPECIFIC BRAND and MODEL/PRODUCT NAME for each item
- Look carefully for: visible logos, brand tags, distinctive design signatures, unique hardware, recognizable patterns
- Common luxury brands: Gucci, Louis Vuitton, Prada, Balenciaga, Chanel, Dior, Hermès, Burberry, Fendi, Versace, Saint Laurent, Bottega Veneta, Loewe, Celine
- Common premium brands: Acne Studios, The Row, Totême, Ganni, Sandro, Maje, AllSaints, COS, Arket, & Other Stories, Filippa K, Tiger of Sweden
- Common streetwear: Nike, Adidas, New Balance, Carhartt WIP, Stüssy, Supreme, Palace, Off-White, Fear of God
- Common fast fashion: Zara, H&M, Mango, ASOS, Uniqlo, Massimo Dutti
- If you recognize a specific product (e.g., "Nike Air Force 1", "Gucci Horsebit loafers"), include the model name
- Even if not 100% certain, provide your best educated guess with appropriate confidence score
- Include ALL visible items, even partially visible ones (with lower confidence)
- Style tags should help with search filtering (e.g., "vintage", "luxury", "athleisure")
- Search keywords should include brand name if identified, plus specific style descriptors
"""


class OutfitAnalyzer:
    """Analyze outfit images to identify clothing items."""

    def __init__(self, client: Optional[GeminiClient] = None):
        self.client = client or get_gemini_client()

    def analyze(
        self,
        image_data: bytes,
        mime_type: str = "image/jpeg",
        custom_prompt: Optional[str] = None,
    ) -> OutfitAnalysis:
        """
        Analyze an outfit image and identify all clothing items.

        Args:
            image_data: Raw image bytes
            mime_type: Image MIME type
            custom_prompt: Optional custom prompt to use instead of default

        Returns:
            OutfitAnalysis with all identified items
        """
        prompt = custom_prompt or OUTFIT_ANALYSIS_PROMPT

        raw_response = self.client.analyze_image(image_data, prompt, mime_type)

        return self._parse_response(raw_response)

    def analyze_from_url(self, image_url: str) -> OutfitAnalysis:
        """Analyze an outfit from an image URL."""
        raw_response = self.client.analyze_image_from_url(
            image_url, OUTFIT_ANALYSIS_PROMPT
        )
        return self._parse_response(raw_response)

    def analyze_from_base64(
        self,
        base64_data: str,
        mime_type: str = "image/jpeg",
    ) -> OutfitAnalysis:
        """Analyze an outfit from base64-encoded image data."""
        raw_response = self.client.analyze_image_from_base64(
            base64_data, OUTFIT_ANALYSIS_PROMPT, mime_type
        )
        return self._parse_response(raw_response)

    def _parse_response(self, raw_response: str) -> OutfitAnalysis:
        """Parse the raw AI response into structured data."""
        try:
            # Extract JSON from response (handle markdown code blocks)
            json_str = raw_response
            if "```json" in raw_response:
                json_str = raw_response.split("```json")[1].split("```")[0]
            elif "```" in raw_response:
                json_str = raw_response.split("```")[1].split("```")[0]

            # Clean up the JSON string
            json_str = json_str.strip()

            data = json.loads(json_str)

            # Parse items
            items = []
            for item_data in data.get("items", []):
                items.append(
                    IdentifiedItem(
                        item_type=item_data.get("item_type", "unknown"),
                        description=item_data.get("description", ""),
                        brand_guess=item_data.get("brand_guess"),
                        color=item_data.get("color", "unknown"),
                        pattern=item_data.get("pattern"),
                        material_guess=item_data.get("material_guess"),
                        style_tags=item_data.get("style_tags", []),
                        confidence=float(item_data.get("confidence", 0.8)),
                        search_keywords=item_data.get("search_keywords", []),
                    )
                )

            return OutfitAnalysis(
                items=items,
                overall_style=data.get("overall_style", ""),
                occasion=data.get("occasion"),
                season=data.get("season"),
                gender=data.get("gender"),
                age_group=data.get("age_group"),
                raw_response=raw_response,
            )

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            # Return partial analysis with raw response
            return OutfitAnalysis(
                items=[],
                overall_style="",
                raw_response=raw_response,
            )

    def generate_search_query(self, item: IdentifiedItem) -> str:
        """Generate an optimized search query for an identified item."""
        parts = []

        # Add brand if known (highest priority)
        if item.brand_guess:
            parts.append(item.brand_guess)

        # Add item type (essential)
        if item.item_type:
            parts.append(item.item_type)

        # Add color (helps narrow results)
        if item.color and item.color.lower() not in ["unknown", "multi", "multicolor"]:
            # Simplify color if it has multiple parts
            color = item.color.split("/")[0].split(",")[0].strip()
            parts.append(color)

        return " ".join(parts)

    def generate_search_params(self, item: IdentifiedItem) -> dict:
        """
        Generate structured search parameters from an identified item.

        Returns a dict that can be used to construct a SearchQuery.
        """
        params = {
            "query": self.generate_search_query(item),
            "category": item.item_type,
            "style_tags": item.style_tags,
        }

        if item.brand_guess:
            params["brand"] = item.brand_guess

        if item.color and item.color.lower() not in ["unknown", "multi", "multicolor"]:
            params["color"] = item.color.split("/")[0].split(",")[0].strip()

        return params


# Module-level convenience function
def analyze_outfit(image_data: bytes, mime_type: str = "image/jpeg") -> OutfitAnalysis:
    """Convenience function to analyze an outfit image."""
    analyzer = OutfitAnalyzer()
    return analyzer.analyze(image_data, mime_type)
