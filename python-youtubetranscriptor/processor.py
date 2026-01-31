import os
import json
from openai import OpenAI
from models import AnalysisResult, CleaningResult, ClaimsResult, Claim, Correction
from prompts import CLEAN_TRANSCRIPT_SYSTEM, EXTRACT_CLAIMS_SYSTEM, SUMMARIZE_SYSTEM


class TranscriptProcessor:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o")

    def _call_llm(self, system: str, user: str, response_format: type | None = None) -> str:
        """Make an LLM call with optional structured output."""
        kwargs = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        
        if response_format:
            kwargs["response_format"] = response_format
        
        response = self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content

    def _chunk_transcript(self, transcript_segments: list[dict], max_tokens: int = 6000) -> list[str]:
        """Split transcript into chunks by natural breaks."""
        chunks = []
        current_chunk = []
        current_length = 0
        
        # Rough estimate: 4 chars per token
        chars_per_token = 4
        max_chars = max_tokens * chars_per_token
        
        for segment in transcript_segments:
            text = segment.get("text", "")
            segment_length = len(text)
            
            # Check for natural break (gap > 2 seconds)
            if current_chunk and segment.get("start", 0) - (current_chunk[-1].get("start", 0) + current_chunk[-1].get("duration", 0)) > 2:
                if current_length > max_chars * 0.5:  # Chunk is reasonably sized
                    chunks.append(" ".join(s.get("text", "") for s in current_chunk))
                    current_chunk = []
                    current_length = 0
            
            if current_length + segment_length > max_chars:
                if current_chunk:
                    chunks.append(" ".join(s.get("text", "") for s in current_chunk))
                current_chunk = [segment]
                current_length = segment_length
            else:
                current_chunk.append(segment)
                current_length += segment_length
        
        if current_chunk:
            chunks.append(" ".join(s.get("text", "") for s in current_chunk))
        
        return chunks if chunks else [""]

    def clean_transcript(self, raw_transcript: str) -> CleaningResult:
        """Stage 1: Clean and correct the transcript."""
        response = self._call_llm(
            system=CLEAN_TRANSCRIPT_SYSTEM,
            user=f"Please clean and correct this transcript:\n\n{raw_transcript}",
            response_format={"type": "json_object"},
        )
        
        data = json.loads(response)
        
        corrections = [
            Correction(
                original=c.get("original", ""),
                corrected=c.get("corrected", ""),
                reason=c.get("reason", ""),
            )
            for c in data.get("corrections", [])
        ]
        
        return CleaningResult(
            cleaned_transcript=data.get("cleaned_transcript", raw_transcript),
            corrections=corrections,
        )

    def extract_claims(self, cleaned_transcript: str) -> list[Claim]:
        """Stage 2 & 3: Extract claims and flag hot takes."""
        response = self._call_llm(
            system=EXTRACT_CLAIMS_SYSTEM,
            user=f"Extract all claims from this transcript:\n\n{cleaned_transcript}",
            response_format={"type": "json_object"},
        )
        
        data = json.loads(response)
        
        claims = []
        for c in data.get("claims", []):
            claims.append(Claim(
                claim=c.get("claim", ""),
                speaker=c.get("speaker"),
                confidence_level=c.get("confidence_level", "medium"),
                topic_tags=c.get("topic_tags", []),
                is_hot_take=c.get("is_hot_take", False),
                hot_take_reason=c.get("hot_take_reason"),
            ))
        
        return claims

    def summarize(self, cleaned_transcript: str) -> str:
        """Generate a brief summary."""
        return self._call_llm(
            system=SUMMARIZE_SYSTEM,
            user=f"Summarize this transcript:\n\n{cleaned_transcript}",
        )

    def process(self, video_id: str, transcript_segments: list[dict]) -> AnalysisResult:
        """Run the full pipeline on a transcript."""
        # Combine segments into raw text
        raw_transcript = " ".join(seg.get("text", "") for seg in transcript_segments)
        
        # Check if we need to chunk
        if len(raw_transcript) > 24000:  # ~6000 tokens
            chunks = self._chunk_transcript(transcript_segments)
        else:
            chunks = [raw_transcript]
        
        # Process each chunk
        all_corrections = []
        all_claims = []
        cleaned_parts = []
        
        for chunk in chunks:
            # Stage 1: Clean
            cleaning_result = self.clean_transcript(chunk)
            cleaned_parts.append(cleaning_result.cleaned_transcript)
            all_corrections.extend(cleaning_result.corrections)
            
            # Stage 2 & 3: Extract claims with hot take detection
            claims = self.extract_claims(cleaning_result.cleaned_transcript)
            all_claims.extend(claims)
        
        # Combine cleaned transcript
        full_cleaned = " ".join(cleaned_parts)
        
        # Generate summary from cleaned transcript
        summary = self.summarize(full_cleaned[:8000])  # Limit for summary
        
        return AnalysisResult(
            video_id=video_id,
            cleaned_transcript=full_cleaned,
            corrections_made=all_corrections,
            claims=all_claims,
            summary=summary,
        )
