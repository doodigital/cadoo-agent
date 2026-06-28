"""Google Veo 3 video generation via the Gemini API.

Uses the `veo-3.0-generate-preview` model (or veo-2) through the
generativelanguage.googleapis.com long-running operations API.

Models:
  veo-3       veo-3.0-generate-preview    Latest, audio support, text+image input
  veo-2       veo-2.0-generate-001        Stable, no audio, text+image input

Selection precedence (first hit wins):
1. ``model=`` arg from the tool call
2. ``GEMINI_VIDEO_MODEL`` env var
3. ``video_gen.gemini.model`` in config.yaml
4. DEFAULT_MODEL

Authentication via ``GEMINI_API_KEY`` or ``GOOGLE_API_KEY``.

The Gemini video API is async (long-running operation). This plugin polls
until the video is ready (up to 5 minutes) before returning.
"""

from __future__ import annotations

import base64
import logging
import os
import time
from typing import Any, Dict, List, Optional

import requests

from agent.video_gen_provider import (
    VideoGenProvider,
    error_response,
    success_response,
)

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "veo-3"
GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"

_MODELS: Dict[str, Dict[str, Any]] = {
    "veo-3": {
        "api_id": "veo-3.0-generate-preview",
        "display": "Veo 3",
        "speed": "~60-120s",
        "strengths": "Latest Google video model, native audio, 8s clips",
        "price": "premium",
        "supports_audio": True,
        "supports_image_input": True,
        "default_duration": 8,
    },
    "veo-2": {
        "api_id": "veo-2.0-generate-001",
        "display": "Veo 2",
        "speed": "~30-90s",
        "strengths": "Stable, high quality, no audio",
        "price": "standard",
        "supports_audio": False,
        "supports_image_input": True,
        "default_duration": 8,
    },
}

_SUPPORTED_ASPECT_RATIOS = ("16:9", "9:16", "1:1")
_SUPPORTED_RESOLUTIONS = ("480p", "720p", "1080p")

POLL_INTERVAL = 5
POLL_TIMEOUT = 360


def _load_config() -> Dict[str, Any]:
    try:
        from cadoo_cli.config import load_config
        cfg = load_config()
        section = cfg.get("video_gen") if isinstance(cfg, dict) else None
        g = section.get("gemini") if isinstance(section, dict) else None
        return g if isinstance(g, dict) else {}
    except Exception as exc:
        logger.debug("Could not load video_gen.gemini config: %s", exc)
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
        os.environ.get("GEMINI_VIDEO_MODEL", ""),
        _load_config().get("model", ""),
        DEFAULT_MODEL,
    ]
    for c in candidates:
        if c and c.strip() in _MODELS:
            return {**_MODELS[c.strip()], "_key": c.strip()}
    return {**_MODELS[DEFAULT_MODEL], "_key": DEFAULT_MODEL}


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


def _poll_operation(op_name: str, api_key: str, meta: Dict[str, Any], prompt: str, aspect: str) -> Dict[str, Any]:
    """Poll a long-running operation until it completes or times out."""
    url = f"{GEMINI_API_BASE}/{op_name}?key={api_key}"
    deadline = time.time() + POLL_TIMEOUT
    while time.time() < deadline:
        time.sleep(POLL_INTERVAL)
        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
        except Exception as exc:
            logger.debug("Poll error: %s", exc)
            continue
        data = resp.json()
        if not data.get("done"):
            logger.debug("Veo operation not done yet: %s", data.get("metadata", {}).get("state"))
            continue
        if "error" in data:
            err = data["error"]
            return error_response(
                error=f"Veo generation failed: {err.get('message', err)}",
                error_type="api_error",
                provider="gemini",
                model=meta["api_id"],
                prompt=prompt,
                aspect_ratio=aspect,
            )
        response_data = data.get("response", {})
        generated = response_data.get("generatedSamples") or response_data.get("videos", [])
        if not generated:
            return error_response(
                error="Veo returned no video samples (may have been filtered).",
                error_type="empty_response",
                provider="gemini",
                model=meta["api_id"],
                prompt=prompt,
                aspect_ratio=aspect,
            )
        sample = generated[0]
        video_uri = (
            sample.get("video", {}).get("uri")
            or sample.get("uri")
            or sample.get("url")
        )
        if video_uri:
            return success_response(
                video=video_uri,
                model=meta["api_id"],
                prompt=prompt,
                modality="image" if meta.get("_used_image") else "text",
                aspect_ratio=aspect,
                duration=meta.get("default_duration", 8),
                provider="gemini",
            )
        return error_response(
            error="Veo returned a sample with no video URI.",
            error_type="empty_response",
            provider="gemini",
            model=meta["api_id"],
            prompt=prompt,
            aspect_ratio=aspect,
        )
    return error_response(
        error=f"Veo generation timed out after {POLL_TIMEOUT}s.",
        error_type="timeout",
        provider="gemini",
        model=meta["api_id"],
        prompt=prompt,
        aspect_ratio=aspect,
    )


class GeminiVideoGenProvider(VideoGenProvider):
    """Google Veo 3 / Veo 2 video generation via Gemini API."""

    @property
    def name(self) -> str:
        return "gemini"

    @property
    def display_name(self) -> str:
        return "Google Veo (Gemini)"

    def is_available(self) -> bool:
        return bool(_resolve_api_key())

    def list_models(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": mid,
                "display": m["display"],
                "speed": m["speed"],
                "strengths": m["strengths"],
                "price": m["price"],
                "tier": "premium",
                "modalities": ["text", "image"] if m["supports_image_input"] else ["text"],
            }
            for mid, m in _MODELS.items()
        ]

    def default_model(self) -> Optional[str]:
        return DEFAULT_MODEL

    def get_setup_schema(self) -> Dict[str, Any]:
        return {
            "name": "Google Veo",
            "badge": "paid",
            "tag": "Veo 3 (audio) & Veo 2 — text-to-video & image-to-video via Gemini API",
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
            "aspect_ratios": list(_SUPPORTED_ASPECT_RATIOS),
            "resolutions": list(_SUPPORTED_RESOLUTIONS),
            "max_duration": 8,
            "min_duration": 5,
            "supports_audio": True,
            "supports_negative_prompt": True,
            "max_reference_images": 1,
        }

    def generate(
        self,
        prompt: str,
        *,
        model: Optional[str] = None,
        image_url: Optional[str] = None,
        reference_image_urls: Optional[List[str]] = None,
        duration: Optional[int] = None,
        aspect_ratio: str = "16:9",
        resolution: str = "720p",
        negative_prompt: Optional[str] = None,
        audio: Optional[bool] = None,
        seed: Optional[int] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        api_key = _resolve_api_key()
        if not api_key:
            return error_response(
                error="No Gemini API key found. Set GEMINI_API_KEY or GOOGLE_API_KEY.",
                error_type="missing_api_key",
                provider="gemini",
            )

        meta = _resolve_model(model)
        api_model = meta["api_id"]

        ar = aspect_ratio if aspect_ratio in _SUPPORTED_ASPECT_RATIOS else "16:9"
        res = resolution if resolution in _SUPPORTED_RESOLUTIONS else "720p"
        dur = duration or meta.get("default_duration", 8)

        source_image: Optional[str] = None
        if isinstance(image_url, str) and image_url.strip():
            source_image = image_url.strip()
        elif reference_image_urls:
            from agent.video_gen_provider import normalize_reference_images as _nri
            refs = _nri(reference_image_urls)  # type: ignore[attr-defined]
            if refs:
                source_image = refs[0]

        if source_image and not meta["supports_image_input"]:
            source_image = None
            logger.warning("Model %s does not support image input; ignoring image_url", api_model)

        video_config: Dict[str, Any] = {
            "durationSeconds": dur,
            "aspectRatio": ar,
            "resolution": res,
        }
        if negative_prompt:
            video_config["negativePrompt"] = negative_prompt
        if meta["supports_audio"] and audio is not False:
            video_config["generateAudio"] = True
        if seed is not None:
            video_config["seed"] = seed

        instance: Dict[str, Any] = {"prompt": prompt}
        if source_image:
            try:
                b64, mime = _load_image_as_base64(source_image)
                instance["image"] = {"bytesBase64Encoded": b64, "mimeType": mime}
                meta = {**meta, "_used_image": True}
            except Exception as exc:
                return error_response(
                    error=f"Could not load source image: {exc}",
                    error_type="io_error",
                    provider="gemini",
                    model=api_model,
                )

        payload = {
            "model": api_model,
            "instances": [instance],
            "parameters": video_config,
        }

        submit_url = f"{GEMINI_API_BASE}/models/{api_model}:predictLongRunning?key={api_key}"
        try:
            resp = requests.post(submit_url, json=payload, timeout=60)
            resp.raise_for_status()
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else 0
            detail = ""
            try:
                detail = exc.response.json().get("error", {}).get("message", "")
            except Exception:
                pass
            return error_response(
                error=f"Veo API error {status}: {detail}",
                error_type="api_error",
                provider="gemini",
                model=api_model,
                prompt=prompt,
            )
        except Exception as exc:
            return error_response(
                error=f"Request failed: {exc}",
                error_type="network_error",
                provider="gemini",
                model=api_model,
                prompt=prompt,
            )

        op_data = resp.json()
        op_name = op_data.get("name", "")
        if not op_name:
            return error_response(
                error="Veo API did not return an operation name.",
                error_type="api_error",
                provider="gemini",
                model=api_model,
                prompt=prompt,
            )

        logger.info("Veo operation started: %s — polling for up to %ds", op_name, POLL_TIMEOUT)
        return _poll_operation(op_name, api_key, {**meta, "api_id": api_model}, prompt, ar)


def register(ctx) -> None:
    """Plugin entry point — wire GeminiVideoGenProvider into the registry."""
    ctx.register_video_gen_provider(GeminiVideoGenProvider())
