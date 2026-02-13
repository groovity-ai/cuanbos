"""
RAG Financial Report Analyzer
Parse PDF financial reports and analyze with LLM.
"""

import json
import io

try:
    from PyPDF2 import PdfReader
except ImportError:
    PdfReader = None

from ai_client import chat_completion

REPORT_PROMPT = """You are CuanBot, an expert financial analyst AI.
I will provide extracted text from a company's financial report (Laporan Keuangan).

Analyze the report and RESPOND IN VALID JSON ONLY with this structure:
{
    "company": "company name if found",
    "period": "reporting period if found",
    "metrics": {
        "revenue": {"value": number_or_null, "unit": "IDR/USD", "yoy_change": "percent or null"},
        "net_profit": {"value": number_or_null, "unit": "IDR/USD", "yoy_change": "percent or null"},
        "total_assets": {"value": number_or_null, "unit": "IDR/USD"},
        "total_debt": {"value": number_or_null, "unit": "IDR/USD"},
        "debt_to_equity": number_or_null,
        "roe": number_or_null,
        "npm": number_or_null,
        "eps": number_or_null
    },
    "highlights": ["key positive/negative finding 1", "finding 2", "finding 3"],
    "risks": ["identified risk 1", "risk 2"],
    "verdict": "Healthy / Warning / Critical",
    "analysis": "3-5 sentence analysis in Bahasa Indonesia (santai tapi data-driven). Jelaskan kondisi keuangan perusahaan."
}

If data is not available in the report, set values to null. Focus on extracting actual numbers.
"""


def extract_pdf_text(pdf_bytes, max_pages=20):
    """Extract text from a PDF file."""
    if PdfReader is None:
        return None, "PyPDF2 not installed"

    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        pages_text = []
        for i, page in enumerate(reader.pages):
            if i >= max_pages:
                break
            text = page.extract_text()
            if text:
                pages_text.append(text)

        full_text = "\n\n".join(pages_text)
        return full_text, None
    except Exception as e:
        return None, f"PDF extraction failed: {str(e)}"


def analyze_report(pdf_bytes):
    """
    Parse a PDF financial report and analyze with LLM.

    Args:
        pdf_bytes: Raw bytes of the PDF file.

    Returns:
        dict with extracted metrics, analysis, and verdict.
    """
    # 1. Extract text
    text, error = extract_pdf_text(pdf_bytes)
    if error:
        return {"error": error}

    if not text or len(text.strip()) < 100:
        return {"error": "PDF contains too little text to analyze"}

    # 2. Truncate if too long (LLM context limit)
    max_chars = 15000
    if len(text) > max_chars:
        text = text[:max_chars] + "\n\n[... truncated ...]"

    # 3. Send to LLM
    messages = [
        {"role": "system", "content": REPORT_PROMPT},
        {"role": "user", "content": f"Here is the financial report text:\n\n{text}"},
    ]

    try:
        response = chat_completion(messages)

        # Parse JSON from response
        cleaned = response.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

        try:
            result = json.loads(cleaned)
            result["pages_extracted"] = len(text.split("\n\n"))
            return result
        except json.JSONDecodeError:
            return {
                "metrics": {},
                "analysis": response,
                "verdict": "Could not parse structured response",
                "raw_response": response,
            }

    except Exception as e:
        return {"error": f"Report analysis failed: {str(e)}"}
