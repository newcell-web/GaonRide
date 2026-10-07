import logging
import os
from datetime import date, timedelta

from pydantic import ValidationError

from backend.config import AI_AVAILABLE, GROQ_API_KEY
from backend.schemas import RideRequestParsed

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------

class AIUnavailableError(Exception):
    """Raised when GROQ_API_KEY is not configured."""
    pass


class AIParseError(Exception):
    """Raised when the LLM response cannot be parsed into RideRequestParsed."""
    pass


# ---------------------------------------------------------------------------
# Groq client — only instantiated when a key is present
# ---------------------------------------------------------------------------

try:
    from groq import Groq
    _client: "Groq | None" = Groq(api_key=GROQ_API_KEY) if AI_AVAILABLE else None
except ImportError:
    _client = None


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _strip_fences(text: str) -> str:
    """Remove markdown code fences (```json ... ``` or ``` ... ```) if present."""
    text = text.strip()
    if text.startswith("```"):
        # Remove the opening fence line
        text = text[text.index("\n") + 1:] if "\n" in text else text[3:]
    if text.endswith("```"):
        text = text[: text.rfind("```")]
    return text.strip()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def transcribe_audio(file_path: str) -> str:
    """Transcribe an audio file using Groq Whisper.

    Always deletes the temp file on exit, success or failure.
    """
    if not AI_AVAILABLE:
        raise AIUnavailableError(
            "Groq API key has not been configured. Add GROQ_API_KEY to the .env file."
        )
    try:
        with open(file_path, "rb") as f:
            transcription = _client.audio.transcriptions.create(
                model="whisper-large-v3",
                file=(os.path.basename(file_path), f, "audio/webm"),
            )
        return transcription.text
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


def parse_request_text(text: str, today: date) -> RideRequestParsed:
    """Parse a natural-language travel request into a RideRequestParsed object."""
    if not AI_AVAILABLE:
        raise AIUnavailableError(
            "Groq API key has not been configured. Add GROQ_API_KEY to the .env file."
        )

    text = (text or "").strip()
    if not text:
        raise AIParseError("No text was provided to parse. Please speak clearly or type your request.")

    tomorrow = (today + timedelta(days=1)).isoformat()
    system_prompt = (
        "You are a JSON-only travel request extractor. "
        "Your output must be a single JSON object and nothing else — no explanation, no markdown, no code fences.\n\n"
        f"Today: {today.isoformat()}. Tomorrow: {tomorrow}.\n"
        "Input language may be English, Hindi, or Assamese.\n\n"
        "Output schema (replace values, keep keys exact):\n"
        '{"origin":"<start place>","destination":"<end place>",'
        f'"travel_date":"<YYYY-MM-DD, tomorrow={tomorrow}>","preferred_time":"<HH:MM 24h, morning=09:00 afternoon=14:00 evening=17:00>",'
        '"passenger_count":<int, speaker counts, me+mother=2>,"language":"<en/hi/as>","notes":<string or null>}'
    )

    def _call_llm(prompt: str) -> str:
        response = _client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": text},
            ],
            temperature=0.1,
            max_tokens=500,
        )
        choice = response.choices[0]
        raw = choice.message.content or ""
        logger.info("LLM finish_reason=%s raw=%r", choice.finish_reason, raw)
        stripped = _strip_fences(raw.strip())
        if not stripped:
            raise AIParseError(
                f"The AI model returned an empty response (finish_reason={choice.finish_reason!r}). "
                "Please try typing your request manually."
            )
        return stripped

    json_str = _call_llm(system_prompt)

    try:
        return RideRequestParsed.model_validate_json(json_str)
    except ValidationError as first_error:
        # Retry once with the validation error appended to the prompt
        retry_prompt = (
            system_prompt
            + f"\n\nYour previous response caused this validation error: {first_error}."
            " Fix it and return only valid JSON."
        )
        json_str = _call_llm(retry_prompt)
        try:
            return RideRequestParsed.model_validate_json(json_str)
        except ValidationError as second_error:
            raise AIParseError(f"Could not parse travel request: {second_error}") from second_error
