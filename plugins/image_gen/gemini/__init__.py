"""Google Gemini Imagen 3 image generation backend.

Uses the Gemini generativelanguage API (`imagen-3.0-generate-002`) for
text-to-image and Gemini 2.0 Flash (`gemini-2.0-flash-exp-image-generation`)
for image-to-image / image editing via the `generate_content` multimodal API.

Models:
  imagen-3          imagen-3.0-generate-002          text-to-image only, highest quality
  gemini-2.0-flash  gemini-2.0-flash-exp-image-generation  text+image editing, faster

Selection precedence (first hit wins):
1. ``model=`` arg from the tool call
2. ``GEMINI_IMAGE_MODEL`` env var
3. ``image_gen.gemini.model`` in config.yaml
4. DEFAULT_MODEL

Authentication via ``GEMINI_API_KEY`` or ``GOOGLE_API_KEY``.
"""

from __future__ import annotations

import base64
import logging
import os
from typing import Any, Dict, List, Optional

import requests

from agent.image_gen_provider import (
    DEFAULT_ASPECT_RATIO,
    ImageGenProvider,
    error_response,
    normalize_reference_images,
    resolve_aspect_ratio,
    save_b64_image,
    success_response,
)

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "imagen-3"
GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"

_MODELS: Dict[str, Dict[str, Any]] = {
    "imagen-3": {
        "api_id": "imagen-3.0-generate-002",
        "display": "Imagen 3",
        "speed": "~5-10s",
        "strengths": "Highest quality photorealistic images, text rendering",
        "supports_image_input": False,
    },
    "gemini-2.0-flash": {
        "api_id": "gemini-2.0-flash-exp-image-generation",
        "display": "Gemini 2.0 Flash (Image Gen)",
        "speed": "~3-8s",
        "strengths": "Image editing, multimodal, faster generation",
        "supports_image_input": True,
    },
}

_IMAGEN_ASPECT_RATIOS = {
    "landscape": "16:9",
    "square": "1:1",
    "portrait": "9:16",
    "4:3": "4:3",
    "3:4": "3:4",
}


def _load_config() -> Dict[str, Any]:
    try:
        from cadoo_cli.config import load_config
        cfg = load_config()
        section = cfg.get("image_gen") if isinstance(cfg, dict) else None
        g = section.get("gemini") if isinstance(section, dict) else None
        return g if isinstance(g, dict) else {}
    except Exception as exc:
        logger.debug("Could not load image_gen.gemini config: %s", exc)
        return {}


def _resolve_api_key() -> str:
    for var in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        val = os.environ.get(var, "").strip()
        if val:
            return val
    return ""


def _resolve_model(model_arg: Optional[str]) -> Dict[str, Any]:
    candidates = [
        model_arg,
        os.environ.get("GEMINI_IMAGE_MODEL", ""),
        _load_config().get("model", ""),
        DEFAULT_MODEL,
    ]
    for c in candidates:
        if c and c.strip() in _MODELS:
            return _MODELS[c.strip()]
    return _MODELS[DEFAULT_MODEL]


class GeminiImageGenProvider(ImageGenProvider):
    """Google Gemini / Imagen 3 image generation backend."""

    @property
    def name(self) -> str:
        return "gemini"

    @property
    def display_name(self) -> str:
        return "Google Gemini (Imagen 3)"

    def is_available(self) -> bool:
        return bool(_resolve_api_key())

    def list_models(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": mid,
                "display": m["display"],
                "speed": m["speed"],
                "strengths": m["strengths"],
            }
            for mid, m in _MODELS.items()
        ]

    def default_model(self) -> Optional[str]:
        return DEFAULT_MODEL

    def get_setup_schema(self) -> Dict[str, Any]:
        return {
            "name": "Google Gemini",
            "badge": "free-tier",
            "tag": "Imagen 3 text-to-image & Gemini 2.0 Flash image editing",
            "env_vars": [
                {
                    "key": "GEMINI_API_KEY",
                    "prompt": "Google AI Studio API key",
                    "url": "https://aistudio.google.com/app/apikey",
                },
            ],
        }

    def capabilities(self) -> Dict[str, Any]:
        return {
            "modalities": ["text", "image"],
            "aspect_ratios": list(_IMAGEN_ASPECT_RATIOS.keys()),
            "max_reference_images": 1,
        }

    def generate(
        self,
        prompt: str,
        aspect_ratio: str = DEFAULT_ASPECT_RATIO,
        *,
        image_url: Optional[str] = None,
        reference_image_urls: Optional[List[str]] = None,
        model: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        api_key = _resolve_api_key()
        if not api_key:
            return error_response(
                error="No Gemini API key found. Set GEMINI_API_KEY or GOOGLE_API_KEY.",
                error_type="missing_api_key",
                provider="gemini",
                aspect_ratio=aspect_ratio,
            )

        meta = _resolve_model(model)
        api_model = meta["api_id"]
        aspect = resolve_aspect_ratio(aspect_ratio)

        source_image: Optional[str] = None
        if isinstance(image_url, str) and image_url.strip():
            source_image = image_url.strip()
        else:
            refs = normalize_reference_images(reference_image_urls)
            if refs:
                source_image = refs[0]

        is_edit = bool(source_image) and meta["supports_image_input"]

        if is_edit:
            return self._generate_gemini_flash(
                prompt=prompt,
                api_key=api_key,
                api_model=api_model,
                source_image=source_image,
                aspect=aspect,
            )
        elif meta["api_id"].startswith("imagen"):
            return self._generate_imagen(
                prompt=prompt,
                api_key=api_key,
                api_model=api_model,
                aspect=aspect,
            )
        else:
            return self._generate_gemini_flash(
                prompt=prompt,
                api_key=api_key,
                api_model=api_model,
                source_image=None,
                aspect=aspect,
            )

    def _generate_imagen(
        self,
        prompt: str,
        api_key: str,
        api_model: str,
        aspect: str,
    ) -> Dict[str, Any]:
        ar = _IMAGEN_ASPECT_RATIOS.get(aspect, "1:1")
        url = f"{GEMINI_API_BASE}/models/{api_model}:predict?key={api_key}"
        payload = {
            "instances": [{"prompt": prompt}],
            "parameters": {
                "sampleCount": 1,
                "aspectRatio": ar,
                "safetyFilterLevel": "block_few",
                "personGeneration": "allow_adult",
            },
        }
        try:
            resp = requests.post(url, json=payload, timeout=90)
            resp.raise_for_status()
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else 0
            detail = ""
            try:
                detail = exc.response.json().get("error", {}).get("message", "")
            except Exception:
                pass
            return error_response(
                error=f"Imagen API error {status}: {detail}",
                error_type="api_error",
                provider="gemini",
                model=api_model,
                prompt=prompt,
                aspect_ratio=aspect,
            )
        except Exception as exc:
            return error_response(
                error=f"Request failed: {exc}",
                error_type="network_error",
                provider="gemini",
                model=api_model,
                prompt=prompt,
                aspect_ratio=aspect,
            )

        data = resp.json()
        predictions = data.get("predictions", [])
        if not predictions:
            return error_response(
                error="Imagen returned no predictions (may have been filtered).",
                error_type="empty_response",
                provider="gemini",
                model=api_model,
                prompt=prompt,
                aspect_ratio=aspect,
            )
        b64 = predictions[0].get("bytesBase64Encoded", "")
        if not b64:
            return error_response(
                error="Imagen returned empty image data.",
                error_type="empty_response",
                provider="gemini",
                model=api_model,
                prompt=prompt,
                aspect_ratio=aspect,
            )
        image_bytes = base64.b64decode(b64)
        mime = predictions[0].get("mimeType", "image/png")
        ext = "png" if "png" in mime else "jpg"
        path = save_b64_image(b64, ext=ext)
        return success_response(
            image=path,
            model=api_model,
            prompt=prompt,
            aspect_ratio=aspect,
            modality="text",
            provider="gemini",
        )

    def _generate_gemini_flash(
        self,
        prompt: str,
        api_key: str,
        api_model: str,
        source_image: Optional[str],
        aspect: str,
    ) -> Dict[str, Any]:
        url = f"{GEMINI_API_BASE}/models/{api_model}:generateContent?key={api_key}"
        parts: list = []

        if source_image:
            try:
                image_data, mime_type = _load_image_as_base64(source_image)
                parts.append({
                    "inline_data": {
                        "mime_type": mime_type,
                        "data": image_data,
                    }
                })
            except Exception as exc:
                return error_response(
                    error=f"Could not load source image: {exc}",
                    error_type="io_error",
                    provider="gemini",
                    model=api_model,
                    prompt=prompt,
                    aspect_ratio=aspect,
                )

        parts.append({"text": prompt})

        payload = {
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]},
        }

        try:
            resp = requests.post(url, json=payload, timeout=90)
            resp.raise_for_status()
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else 0
            detail = ""
            try:
                detail = exc.response.json().get("error", {}).get("message", "")
            except Exception:
                pass
            return error_response(
                error=f"Gemini API error {status}: {detail}",
                error_type="api_error",
                provider="gemini",
                model=api_model,
                prompt=prompt,
                aspect_ratio=aspect,
            )
        except Exception as exc:
            return error_response(
                error=f"Request failed: {exc}",
                error_type="network_error",
                provider="gemini",
                model=api_model,
                prompt=prompt,
                aspect_ratio=aspect,
            )

        data = resp.json()
        candidates = data.get("candidates", [])
        for candidate in candidates:
            for part in candidate.get("content", {}).get("parts", []):
                inline = part.get("inline_data")
                if inline:
                    b64 = inline.get("data", "")
                    mime = inline.get("mime_type", "image/png")
                    ext = "png" if "png" in mime else "jpg"
                    path = save_b64_image(b64, ext=ext)
                    return success_response(
                        image=path,
                        model=api_model,
                        prompt=prompt,
                        aspect_ratio=aspect,
                        modality="image" if source_image else "text",
                        provider="gemini",
                    )

        return error_response(
            error="Gemini returned no image data (may have been filtered).",
            error_type="empty_response",
            provider="gemini",
            model=api_model,
            prompt=prompt,
            aspect_ratio=aspect,
        )


def _load_image_as_base64(source: str):
    """Load image from URL or file path, return (base64_str, mime_type)."""
    if source.startswith("data:"):
        header, b64 = source.split(",", 1)
        mime = header.split(";")[0].replace("data:", "")
        return b64, mime
    if source.startswith("http://") or source.startswith("https://"):
        resp = requests.get(source, timeout=30)
        resp.raise_for_status()
        mime = resp.headers.get("content-type", "image/jpeg").split(";")[0]
        return base64.b64encode(resp.content).decode(), mime
    path = os.path.expanduser(source)
    with open(path, "rb") as f:
        data = f.read()
    ext = os.path.splitext(path)[1].lower()
    mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}.get(ext.lstrip("."), "image/jpeg")
    return base64.b64encode(data).decode(), mime


def register(ctx) -> None:
    """Plugin entry point — wire GeminiImageGenProvider into the registry."""
    ctx.register_image_gen_provider(GeminiImageGenProvider())
