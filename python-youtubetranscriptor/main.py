from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import PlainTextResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from youtube_transcript_api import YouTubeTranscriptApi
import os
from youtube_transcript_api.formatters import (
    JSONFormatter,
    TextFormatter,
    SRTFormatter,
    WebVTTFormatter,
)
from typing import Literal
from dotenv import load_dotenv
from models import AnalysisResult
from processor import TranscriptProcessor

load_dotenv()

app = FastAPI(
    title="YouTube Transcript API",
    description="Fetch transcripts from YouTube videos",
)

# Serve static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

ytt_api = YouTubeTranscriptApi()
processor = TranscriptProcessor()


@app.get("/")
def root():
    """Serve the UI."""
    return FileResponse(os.path.join(static_dir, "index.html"))


@app.get("/transcript/{video_id}")
def get_transcript(
    video_id: str,
    languages: str = Query("en", description="Comma-separated language codes, e.g. 'en,de'"),
    format: Literal["json", "text", "srt", "vtt"] = Query("json", description="Output format"),
):
    """Fetch transcript for a YouTube video."""
    lang_list = [lang.strip() for lang in languages.split(",")]

    try:
        transcript = ytt_api.fetch(video_id, languages=lang_list)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

    if format == "json":
        return transcript.to_raw_data()
    
    formatters = {
        "text": TextFormatter(),
        "srt": SRTFormatter(),
        "vtt": WebVTTFormatter(),
    }
    formatted = formatters[format].format_transcript(transcript)
    
    content_types = {
        "text": "text/plain",
        "srt": "application/x-subrip",
        "vtt": "text/vtt",
    }
    return PlainTextResponse(content=formatted, media_type=content_types[format])


@app.get("/transcripts/{video_id}/list")
def list_transcripts(video_id: str):
    """List all available transcripts for a YouTube video."""
    try:
        transcript_list = ytt_api.list(video_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

    return [
        {
            "language": t.language,
            "language_code": t.language_code,
            "is_generated": t.is_generated,
            "is_translatable": t.is_translatable,
        }
        for t in transcript_list
    ]


@app.post("/analyze/{video_id}")
def analyze_transcript(
    video_id: str,
    languages: str = Query("en", description="Comma-separated language codes"),
) -> AnalysisResult:
    """Analyze a YouTube transcript: clean, extract claims, flag hot takes."""
    lang_list = [lang.strip() for lang in languages.split(",")]

    try:
        transcript = ytt_api.fetch(video_id, languages=lang_list)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

    # Get raw transcript data as list of segments
    segments = transcript.to_raw_data()

    try:
        result = processor.process(video_id, segments)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

    return result
