"""Image identification endpoint."""

import base64
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from src.core.outfit_analyzer import OutfitAnalyzer, OutfitAnalysis, IdentifiedItem

router = APIRouter()


class IdentifyRequest(BaseModel):
    """Request for URL-based identification."""

    image_url: Optional[str] = None
    image_base64: Optional[str] = None


class IdentifyResponse(BaseModel):
    """Response from outfit identification."""

    items: list[dict]
    overall_style: str
    occasion: Optional[str]
    season: Optional[str]
    gender: Optional[str]
    age_group: Optional[str]


@router.post("/identify", response_model=IdentifyResponse)
async def identify_outfit(
    file: Optional[UploadFile] = File(None),
    image_url: Optional[str] = Form(None),
    image_base64: Optional[str] = Form(None),
):
    """
    Identify clothing items in an uploaded image.

    Accepts image via:
    - File upload (multipart/form-data)
    - URL reference
    - Base64 encoded data
    """
    analyzer = OutfitAnalyzer()

    try:
        if file:
            # Handle file upload
            content = await file.read()
            content_type = file.content_type or "image/jpeg"
            analysis = analyzer.analyze(content, mime_type=content_type)

        elif image_url:
            # Handle URL
            analysis = analyzer.analyze_from_url(image_url)

        elif image_base64:
            # Handle base64
            analysis = analyzer.analyze_from_base64(image_base64)

        else:
            raise HTTPException(
                status_code=400,
                detail="No image provided. Send file, image_url, or image_base64",
            )

        return IdentifyResponse(
            items=[
                {
                    "item_type": item.item_type,
                    "description": item.description,
                    "brand_guess": item.brand_guess,
                    "color": item.color,
                    "pattern": item.pattern,
                    "material_guess": item.material_guess,
                    "style_tags": item.style_tags,
                    "confidence": item.confidence,
                    "search_keywords": item.search_keywords,
                }
                for item in analysis.items
            ],
            overall_style=analysis.overall_style,
            occasion=analysis.occasion,
            season=analysis.season,
            gender=analysis.gender,
            age_group=analysis.age_group,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.post("/identify/json")
async def identify_outfit_json(request: IdentifyRequest):
    """
    Identify clothing items from JSON body.

    Alternative endpoint accepting JSON instead of form data.
    """
    analyzer = OutfitAnalyzer()

    try:
        if request.image_url:
            analysis = analyzer.analyze_from_url(request.image_url)
        elif request.image_base64:
            analysis = analyzer.analyze_from_base64(request.image_base64)
        else:
            raise HTTPException(
                status_code=400,
                detail="No image provided. Send image_url or image_base64",
            )

        return IdentifyResponse(
            items=[
                {
                    "item_type": item.item_type,
                    "description": item.description,
                    "brand_guess": item.brand_guess,
                    "color": item.color,
                    "pattern": item.pattern,
                    "material_guess": item.material_guess,
                    "style_tags": item.style_tags,
                    "confidence": item.confidence,
                    "search_keywords": item.search_keywords,
                }
                for item in analysis.items
            ],
            overall_style=analysis.overall_style,
            occasion=analysis.occasion,
            season=analysis.season,
            gender=analysis.gender,
            age_group=analysis.age_group,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
