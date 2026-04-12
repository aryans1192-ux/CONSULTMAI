"""
orchestrator.py
Main pipeline. This is the only entry point app.py needs.

Flow:
  user_input
    → extract_facts()          (ai_engine: metrics, urgency, industry, stage)
    → retrieve_context()       (knowledge: embed query → ChromaDB → top-k chunks)
    → call_llm()               (llm_client: build prompt from facts + chunks → LLM)
    → return (response, facts, retrieved_chunks)
"""

from __future__ import annotations


def process(user_input: str) -> tuple[str, dict, list[dict]]:
    """
    Returns (response_text, facts_dict, retrieved_chunks).
    app.py can use facts_dict for the Thinking panel and chips.
    retrieved_chunks is available for debugging / transparency UI.
    """
    from ai_engine import extract_facts
    from knowledge.embedder import embed
    from knowledge.store import retrieve, is_empty
    from ingestion.ingest import ingest_all
    from llm_client import call_llm

    # 1. Extract lightweight facts from the raw input
    facts = extract_facts(user_input)

    # 2. Ensure the knowledge store is populated (skip if chromadb not installed)
    chunks = []
    try:
        if is_empty():
            ingest_all()
        # 3. Retrieve the most relevant knowledge chunks
        query_vec = embed(user_input)
        chunks = retrieve(query_vec, top_k=6)
    except ImportError:
        pass  # chromadb not installed yet — LLM will reason from first principles

    # 4. Generate response with real retrieved context
    response = call_llm(facts, retrieved_chunks=chunks)

    return response, facts, chunks
