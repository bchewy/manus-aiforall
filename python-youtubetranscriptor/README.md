# YouTube Transcript API

FastAPI wrapper for fetching YouTube video transcripts.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
uvicorn main:app --reload
```

## Endpoints

### GET `/transcript/{video_id}`

Fetch transcript for a video.

**Query params:**
- `languages` - Comma-separated language codes (default: `en`)
- `format` - Output format: `json`, `text`, `srt`, `vtt` (default: `json`)

**Examples:**
```bash
# JSON format
curl "http://localhost:8000/transcript/dQw4w9WgXcQ"

# Plain text
curl "http://localhost:8000/transcript/dQw4w9WgXcQ?format=text"

# SRT subtitles
curl "http://localhost:8000/transcript/dQw4w9WgXcQ?format=srt"

# German transcript
curl "http://localhost:8000/transcript/dQw4w9WgXcQ?languages=de,en"
```

### GET `/transcripts/{video_id}/list`

List all available transcripts for a video.

```bash
curl "http://localhost:8000/transcripts/dQw4w9WgXcQ/list"
```

## Docs

Interactive API docs at `http://localhost:8000/docs`
