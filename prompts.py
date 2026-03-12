"""
prompts.py — Centralized prompt management for GDrive Summarizer.

Storing prompts in a separate file improves maintainability, allows for 
easier A/B testing, and keeps the core logic of the summarizer clean.
"""

# System instruction ensures the model maintains a professional tone and specific constraints
SYSTEM_INSTRUCTION = (
    "You are an expert document analyst. Produce clear, accurate, and professional "
    "summaries of documents. Focus on the most important information: key arguments, "
    "findings, decisions, or takeaways. Write in clear English using complete sentences. "
    "Do not include meta-commentary about the document format or your own capabilities."
)

# User-facing prompt with placeholders for dynamic content
SUMMARY_PROMPT = """Please summarize the following document in 5–10 sentences.
Focus on the main purpose, key points, conclusions, and any critical details
a reader would need to understand the document without reading it in full.

Document title: {file_name}

Document content:
{text}

Summary:"""
