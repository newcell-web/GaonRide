"""Voice router: audio transcription and NL parsing."""

import os
import tempfile
from datetime import date

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from backend.schemas import ParseResponse, TranscribeResponse
from backend.services.groq_service import (
    AIParseError,
    AIUnavailableError,
    parse_request_text,
    transcribe_audio,
)

router = APIRouter(prefix="/voice", tags=["voice"])

_MAX_AUDIO_BYTES = 10 * 1024 * 1024  # 10 MB


class _ParseBody(BaseModel):
    text: str


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe(file: UploadFile = File(...)) -> TranscribeResponse:
    """Transcribe an uploaded audio file via Groq Whisper."""
    if not file.content_type or not file.content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="File must be an audio file")

    data = await file.read(_MAX_AUDIO_BYTES + 1)
    if len(data) > _MAX_AUDIO_BYTES:
        raise HTTPException(status_code=413, detail="Audio file must be smaller than 10 MB")

    os.makedirs("tmp_audio", exist_ok=True)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm", dir="tmp_audio") as tmp:
        tmp.write(data)
        tmp_path = tmp.name

    try:
        result = transcribe_audio(tmp_path)
        return TranscribeResponse(text=result)
    except AIUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        err_str = str(e)
        if "invalid_api_key" in err_str or "401" in err_str or "Authentication" in err_str:
            raise HTTPException(
                status_code=503,
                detail="Groq API key is invalid. Please check your GROQ_API_KEY in the .env file and restart the server.",
            )
        raise HTTPException(status_code=500, detail=f"Transcription failed: {e}")


@router.post("/parse", response_model=ParseResponse)
async def parse(body: _ParseBody) -> ParseResponse:
    """Parse a natural-language travel request into structured fields."""
    try:
        result = parse_request_text(body.text, date.today())
        return ParseResponse(
            parsed=result,
            raw_text=body.text,
            note="Interpreted by AI from your request",
        )
    except AIUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except AIParseError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        err_str = str(e)
        if "invalid_api_key" in err_str or "401" in err_str or "Authentication" in err_str:
            raise HTTPException(status_code=503, detail="Groq API key is invalid. Check GROQ_API_KEY in .env and restart the server.")
        if "model_not_found" in err_str or "404" in err_str:
            raise HTTPException(status_code=503, detail=f"Groq model not available on this account: {e}")
        raise HTTPException(status_code=500, detail=f"Parse failed: {e}")
