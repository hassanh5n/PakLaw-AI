"""
Module: generator
Purpose: Constructs the LLM prompt from retrieved chunks and calls Groq to generate a cited answer.
Inputs: Original query string, list of top-10 chunk dicts.
Outputs: Answer string with citations.
Dependencies: groq, prompts
"""
