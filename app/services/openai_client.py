"""OpenAI Chat Completions API client with structured JSON outputs."""

from __future__ import annotations

import json
import time
from typing import Any

import structlog
from openai import OpenAI

from app.config import settings

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# JSON Schema for structured output (PO extraction)
# ---------------------------------------------------------------------------

PO_EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "po_primary": {
            "type": ["string", "null"],
            "description": "Primary PO number found, or null if none found",
        },
        "po_secondary": {
            "type": ["string", "null"],
            "description": "Secondary/alternative PO number, or null",
        },
        "po_numbers": {
            "type": "array",
            "items": {"type": "string"},
            "description": "All PO numbers found in the document (may be more than 2). The first entry should match po_primary, the second po_secondary.",
        },
        "supplier": {
            "type": ["string", "null"],
            "description": "Supplier/vendor name if identifiable, or null",
        },
        "confidence": {
            "type": "number",
            "description": "Confidence score from 0.0 to 1.0",
        },
        "found_keywords": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of PO-introducing keywords found in the text",
        },
        "evidence": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "page": {"type": "integer", "description": "0-based page number"},
                    "snippet": {
                        "type": "string",
                        "description": "Text snippet showing the PO in context",
                    },
                },
                "required": ["page", "snippet"],
                "additionalProperties": False,
            },
            "description": "Evidence snippets showing where POs were found",
        },
    },
    "required": [
        "po_primary",
        "po_secondary",
        "po_numbers",
        "supplier",
        "confidence",
        "found_keywords",
        "evidence",
    ],
    "additionalProperties": False,
}


def _get_client() -> OpenAI:
    """Create an OpenAI client."""
    return OpenAI(api_key=settings.openai_api_key)


def call_openai_structured(
    system_prompt: str,
    user_content: str,
    model: str | None = None,
    max_retries: int = 3,
) -> dict[str, Any]:
    """Call OpenAI Chat Completions API with structured JSON output.

    Uses response_format={"type": "json_schema", ...} for guaranteed valid JSON.
    Falls back to response_format={"type": "json_object"} if json_schema is not
    supported by the model/library version.

    Args:
        system_prompt: System instructions for the LLM.
        user_content: The document text to analyse.
        model: Model to use (defaults to settings.openai_model).
        max_retries: Number of retries on failure.

    Returns:
        Parsed JSON dict matching PO_EXTRACTION_SCHEMA.
    """
    model = model or settings.openai_model
    client = _get_client()

    for attempt in range(1, max_retries + 1):
        try:
            logger.info("openai_call_start", model=model, attempt=attempt)

            # Try json_schema format first (requires openai >= 1.40)
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content},
                    ],
                    response_format={
                        "type": "json_schema",
                        "json_schema": {
                            "name": "po_extraction",
                            "schema": PO_EXTRACTION_SCHEMA,
                            "strict": True,
                        },
                    },
                    temperature=0.1,
                )
            except Exception:
                # Fallback: use json_object format (broader compatibility)
                logger.info("json_schema_fallback", model=model)
                # Append schema instructions to the system prompt
                schema_instruction = (
                    "\n\nYou MUST respond with valid JSON matching this exact schema:\n"
                    + json.dumps(PO_EXTRACTION_SCHEMA, indent=2)
                )
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt + schema_instruction},
                        {"role": "user", "content": user_content},
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.1,
                )

            # Extract the text content from the response
            raw_text = response.choices[0].message.content
            result = json.loads(raw_text)

            logger.info(
                "openai_call_success",
                model=model,
                po_primary=result.get("po_primary"),
                confidence=result.get("confidence"),
            )
            return result

        except Exception as exc:
            logger.warning(
                "openai_call_failed",
                model=model,
                attempt=attempt,
                error=str(exc),
            )
            if attempt < max_retries:
                wait = 2 ** attempt
                time.sleep(wait)
            else:
                logger.error("openai_call_exhausted", model=model, error=str(exc))
                # Return empty result on total failure
                return {
                    "po_primary": None,
                    "po_secondary": None,
                    "po_numbers": [],
                    "supplier": None,
                    "confidence": 0.0,
                    "found_keywords": [],
                    "evidence": [],
                }
