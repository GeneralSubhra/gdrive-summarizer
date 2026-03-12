"""
summarizer.py — AI-powered document summarization via Azure OpenAI.

Required environment variables:
  AZURE_OPENAI_API_KEY
  AZURE_OPENAI_ENDPOINT
  AZURE_OPENAI_DEPLOYMENT
  AZURE_OPENAI_API_VERSION
"""

import os
from openai import AzureOpenAI
from parser import truncate_text

# Load configuration from environment
API_KEY = os.environ.get("AZURE_OPENAI_API_KEY", "")
ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT", "")
DEPLOYMENT = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
API_VERSION = os.environ.get("AZURE_OPENAI_API_VERSION", "2024-05-01-preview")

SYSTEM_INSTRUCTION = (
    "You are an expert document analyst. Produce clear, accurate, and professional "
    "summaries of documents. Focus on the most important information: key arguments, "
    "findings, decisions, or takeaways. Write in clear English using complete sentences. "
    "Do not include meta-commentary about the document format or your own capabilities."
)

SUMMARY_PROMPT = """Please summarize the following document in 5–10 sentences.
Focus on the main purpose, key points, conclusions, and any critical details
a reader would need to understand the document without reading it in full.

Document title: {file_name}

Document content:
{text}

Summary:"""


def summarize_text(text: str, file_name: str = "document") -> str:
    """
    Summarize document text using Azure OpenAI.

    Args:
        text:      Extracted plain text of the document.
        file_name: Original file name (used as context for the model).

    Returns:
        A 5–10 sentence summary string.
    """
    if not API_KEY or not ENDPOINT:
        raise RuntimeError(
            "Azure OpenAI credentials missing. Please check AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT in your .env file."
        )

    # Initialize Azure OpenAI client
    print(f"    [Azure OpenAI] Using deployment: {DEPLOYMENT}")
    client = AzureOpenAI(
        api_key=API_KEY,
        api_version=API_VERSION,
        azure_endpoint=ENDPOINT
    )

    # Truncate to avoid hitting context limits (though gpt-4o has a large window)
    truncated = truncate_text(text, max_chars=30_000)
    prompt = SUMMARY_PROMPT.format(file_name=file_name, text=truncated)

    try:
        response = client.chat.completions.create(
            model=DEPLOYMENT,
            messages=[
                {"role": "system", "content": SYSTEM_INSTRUCTION},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1024,
            temperature=0.3,
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        raise RuntimeError(f"Azure OpenAI summarization failed: {e}") from e
