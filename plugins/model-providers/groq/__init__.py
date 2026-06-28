"""Groq provider profile.

Groq uses an OpenAI-compatible chat completions API at api.groq.com.
Free tier available — no credit card required.

Authentication: GROQ_API_KEY (console.groq.com/keys)
Free models: llama-3.3-70b-versatile, llama-3.1-8b-instant, gemma2-9b-it,
             mixtral-8x7b-32768 (subject to rate limits on the free tier).
"""

from __future__ import annotations

from providers import register_provider
from providers.base import ProviderProfile

groq = ProviderProfile(
    name="groq",
    aliases=("groq-cloud",),
    env_vars=("GROQ_API_KEY",),
    display_name="Groq",
    description="Groq (Free tier — llama-3.3-70b, gemma2-9b; set GROQ_API_KEY)",
    signup_url="https://console.groq.com/keys",
    base_url="https://api.groq.com/openai/v1",
    fallback_models=(
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "gemma2-9b-it",
        "mixtral-8x7b-32768",
        "llama3-70b-8192",
        "llama3-8b-8192",
    ),
    default_aux_model="llama-3.1-8b-instant",
)

register_provider(groq)
