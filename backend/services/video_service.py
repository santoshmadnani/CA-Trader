"""
video_service.py - Google Veo 3.1 & Gemini AI Video Generation Engine
Supports asynchronous video generation, long-running operation polling,
binary streaming/downloading, and Gemini prompt enhancement.
"""

import os
import time
import json
import logging
import requests
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger("ca_trader.video_service")

BASE_API_URL = "https://generativelanguage.googleapis.com/v1beta"
DEFAULT_MODEL = "models/veo-3.1-fast-generate-preview"
CINEMATIC_MODEL = "models/veo-3.1-generate-preview"


def get_api_key(custom_key: Optional[str] = None) -> str:
    if custom_key and str(custom_key).strip():
        return str(custom_key).strip()
    return os.getenv("GEMINI_API_KEY", "").strip()


def get_api_headers(api_key: str) -> Dict[str, str]:
    return {
        "x-goog-api-key": api_key,
        "Content-Type": "application/json",
    }


def start_video_generation(
    prompt: str,
    model: str = DEFAULT_MODEL,
    aspect_ratio: str = "16:9",
    duration_seconds: int = 4,
    sample_count: int = 1,
    custom_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Submits a video generation task to Google's Veo predictLongRunning endpoint.
    Returns operation metadata including operation name.
    """
    key = get_api_key(custom_key)
    if not key:
        return {"ok": False, "error": "Gemini API key is not configured. Please configure your key in settings."}

    # Normalize model name
    clean_model = model.strip()
    if not clean_model.startswith("models/"):
        clean_model = f"models/{clean_model}"

    url = f"{BASE_API_URL}/{clean_model}:predictLongRunning"

    # Veo requires durationSeconds to be between 4 and 8
    dur = int(duration_seconds)
    if dur not in (4, 5, 6, 7, 8):
        dur = 4

    payload = {
        "instances": [
            {
                "prompt": prompt.strip()
            }
        ],
        "parameters": {
            "sampleCount": sample_count,
            "aspectRatio": aspect_ratio,
            "durationSeconds": dur,
        }
    }

    try:
        resp = requests.post(url, headers=get_api_headers(key), json=payload, timeout=30)
        data = resp.json()

        if resp.status_code == 429:
            msg = data.get("error", {}).get("message", "Quota exceeded.")
            return {
                "ok": False,
                "status_code": 429,
                "error": f"Google Veo Quota / Billing Limit: {msg} (Ensure your Google Cloud / AI Studio project has billing enabled for Veo video generation)."
            }

        if resp.status_code >= 400:
            error_msg = data.get("error", {}).get("message") or resp.text
            logger.error(f"Veo predictLongRunning failed ({resp.status_code}): {error_msg}")
            return {"ok": False, "status_code": resp.status_code, "error": f"Veo API Error: {error_msg}"}

        op_name = data.get("name")
        if not op_name:
            return {"ok": False, "error": "No operation name returned from Veo API."}

        return {
            "ok": True,
            "operation_name": op_name,
            "model": clean_model,
            "status": "generating",
            "metadata": data.get("metadata", {})
        }

    except Exception as e:
        logger.exception(f"Exception calling Veo predictLongRunning: {e}")
        return {"ok": False, "error": f"Network exception: {str(e)}"}


def check_operation_status(operation_name: str, custom_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Polls the long-running operation status from Google's Generative Language API.
    Returns { done: bool, video_uri: str, error: str, metadata: dict }.
    """
    key = get_api_key(custom_key)
    if not key:
        return {"ok": False, "error": "Gemini API key is not configured."}

    clean_op = operation_name.strip()
    if clean_op.startswith("/"):
        clean_op = clean_op[1:]

    url = f"{BASE_API_URL}/{clean_op}"

    try:
        resp = requests.get(url, headers=get_api_headers(key), timeout=20)
        data = resp.json()

        if resp.status_code >= 400:
            error_msg = data.get("error", {}).get("message") or resp.text
            return {"ok": False, "error": f"Polling error ({resp.status_code}): {error_msg}"}

        is_done = bool(data.get("done", False))
        metadata = data.get("metadata", {})

        if not is_done:
            return {
                "ok": True,
                "done": False,
                "status": "generating",
                "metadata": metadata
            }

        # Check if operation completed with an error
        if "error" in data:
            err = data["error"].get("message") or str(data["error"])
            return {
                "ok": False,
                "done": True,
                "status": "failed",
                "error": err
            }

        # Operation is done successfully; extract video URI
        response_data = data.get("response", {})
        generated_videos = response_data.get("generatedVideos", [])

        if not generated_videos:
            return {
                "ok": False,
                "done": True,
                "status": "failed",
                "error": "Operation completed but no generatedVideos found in response."
            }

        video_uri = generated_videos[0].get("video", {}).get("uri")
        if not video_uri:
            return {
                "ok": False,
                "done": True,
                "status": "failed",
                "error": "Video object did not contain a download URI."
            }

        return {
            "ok": True,
            "done": True,
            "status": "completed",
            "video_uri": video_uri,
            "metadata": metadata
        }

    except Exception as e:
        logger.exception(f"Exception checking operation {operation_name}: {e}")
        return {"ok": False, "error": f"Polling exception: {str(e)}"}


def download_video_file(video_uri: str, target_path: str, custom_key: Optional[str] = None) -> Tuple[bool, Optional[str]]:
    """
    Downloads the generated MP4 video from Google's protected URI using the API key.
    Saves binary stream to target_path.
    """
    key = get_api_key(custom_key)
    if not key:
        return False, "GEMINI_API_KEY is not configured."

    headers = {
        "x-goog-api-key": key
    }

    try:
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        # Google video URIs require following redirects and header authentication
        resp = requests.get(video_uri, headers=headers, stream=True, allow_redirects=True, timeout=120)

        if resp.status_code >= 400:
            # Try appending key as query param fallback
            fallback_url = f"{video_uri}&key={key}" if "?" in video_uri else f"{video_uri}?key={key}"
            resp = requests.get(fallback_url, stream=True, allow_redirects=True, timeout=120)

        if resp.status_code >= 400:
            return False, f"Failed to download video ({resp.status_code}): {resp.text[:200]}"

        with open(target_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=65536):
                if chunk:
                    f.write(chunk)

        if os.path.exists(target_path) and os.path.getsize(target_path) > 1024:
            return True, None
        else:
            return False, "Downloaded video file is empty or corrupted."

    except Exception as e:
        logger.exception(f"Error downloading video from {video_uri}: {e}")
        return False, str(e)


def enhance_prompt_with_gemini(user_idea: str, custom_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Uses Gemini 3.6 Flash to expand a simple user concept into 3 cinematic,
    highly-detailed prompts optimized for Google Veo 3.1 video generation.
    """
    key = get_api_key(custom_key)
    if not key:
        return {"ok": False, "error": "GEMINI_API_KEY is missing."}

    system_instruction = (
        "You are an award-winning Hollywood cinematographer and AI video prompt director. "
        "The user will give you a simple video concept. Expand it into 3 distinct, highly vivid "
        "prompt options optimized for Google Veo 3.1 video generation.\n"
        "Each option must be 35-65 words and describe camera movement, lighting, colors, lens, and atmospheric dynamics.\n"
        "Return strictly valid JSON with key 'options' containing an array of 3 objects: "
        "[{'title': 'Descriptive Title', 'style': 'Cinematic/Sci-Fi/Documentary/Anime/etc', 'prompt': 'Full expanded prompt'}]."
    )

    url = f"{BASE_API_URL}/models/gemini-3.6-flash:generateContent?key={key}"
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": f"{system_instruction}\n\nUser Concept: {user_idea}\nReturn strictly JSON."}
                ]
            }
        ]
    }

    try:
        resp = requests.post(url, json=payload, timeout=20)
        data = resp.json()
        candidates = data.get("candidates", [])
        if candidates:
            raw_text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            clean_json = raw_text.strip()
            if clean_json.startswith("```json"):
                clean_json = clean_json[7:]
            if clean_json.startswith("```"):
                clean_json = clean_json[3:]
            if clean_json.endswith("```"):
                clean_json = clean_json[:-3]
            clean_json = clean_json.strip()

            parsed = json.loads(clean_json)
            options = parsed.get("options", [])
            if options:
                return {"ok": True, "options": options}

    except Exception as e:
        logger.warning(f"Error enhancing prompt with Gemini: {e}")

    # High quality fallback expansions
    return {
        "ok": True,
        "options": [
            {
                "title": "Cinematic Masterpiece",
                "style": "Cinematic",
                "prompt": f"Dramatic cinematic wide shot of {user_idea}, 35mm anamorphic lens, volumetric golden hour lighting, subtle camera push-in, shallow depth of field, photorealistic 8k render."
            },
            {
                "title": "Moody Cyberpunk / Neon",
                "style": "Sci-Fi",
                "prompt": f"Atmospheric nocturnal scene of {user_idea}, vibrant cyan and magenta neon reflections on wet asphalt, light fog, low-angle tracking shot, hyper-detailed futuristic aesthetic."
            },
            {
                "title": "Documentary Hyper-Realism",
                "style": "Documentary",
                "prompt": f"National Geographic style slow-motion 4k footage of {user_idea}, crisp natural morning sunlight, fine texture details, organic handheld camera motion, authentic high-speed capture."
            }
        ]
    }


def generate_video_huggingface(
    prompt: str,
    model: str = "larryvrh/MiniMax-H3-Turbo-Lora",
    provider: str = "wavespeed",
    custom_token: Optional[str] = None,
) -> Tuple[bool, Any]:
    """
    Generates video using Hugging Face InferenceClient with providers such as WaveSpeed or Fal.ai.
    Returns (True, video_bytes) on success, or (False, error_string) on failure.
    """
    token = (custom_token or "").strip() or os.getenv("HF_TOKEN", "").strip() or os.getenv("HUGGINGFACE_TOKEN", "").strip()
    if not token:
        return False, "Hugging Face token (HF_TOKEN) is required. Please paste your token in the API Key box or set HF_TOKEN on the server."

    try:
        from huggingface_hub import InferenceClient
        client = InferenceClient(
            provider=provider,
            api_key=token
        )
        video_bytes = client.text_to_video(
            prompt,
            model=model
        )
        if video_bytes and len(video_bytes) > 500:
            return True, video_bytes
        return False, "Hugging Face returned empty video bytes."
    except Exception as e:
        logger.exception(f"Hugging Face video generation failed: {e}")
        return False, f"Hugging Face ({provider}) error: {str(e)}"


