"""RAG pipeline tests: chunking, TF-IDF retrieval, and pipeline integration."""

from __future__ import annotations

from app.agents.pipeline import run_review_pipeline
from app.services.rag import TfidfEmbedder, chunk_markdown, cosine, get_knowledge_base


def test_knowledge_base_indexes_all_docs():
    kb = get_knowledge_base()
    doc_ids = {c.doc_id for c in kb.chunks}
    assert any(d.startswith("guides/") for d in doc_ids)
    assert any(d.startswith("job_descriptions/") for d in doc_ids)
    assert len(kb.chunks) > 20


def test_search_returns_relevant_guide():
    kb = get_knowledge_base()
    hits = kb.search("quantify impact with metrics and numbers", top_k=4)
    assert hits
    titles = " ".join(chunk.title.lower() for chunk, _ in hits)
    assert "quantif" in titles or "metric" in titles


def test_search_scores_are_sorted_descending():
    kb = get_knowledge_base()
    hits = kb.search("action verbs for resume bullets", top_k=5)
    scores = [score for _, score in hits]
    assert scores == sorted(scores, reverse=True)


def test_chunk_markdown_splits_on_headings():
    doc = "# Title\n\nIntro para.\n\n## Section A\n\nContent A.\n\n## Section B\n\nContent B."
    chunks = chunk_markdown("doc.md", doc)
    assert len(chunks) == 3
    assert all(c.title == "Title" for c in chunks)


def test_tfidf_cosine_prefers_matching_doc():
    embedder = TfidfEmbedder()
    corpus = [
        "python fastapi backend rest api",
        "watercolor painting landscape brushes",
    ]
    embedder.fit(corpus)
    query = embedder.embed("building a fastapi python service")
    assert cosine(query, embedder.embed(corpus[0])) > cosine(query, embedder.embed(corpus[1]))


def test_pipeline_records_trace_and_uses_rule_based(sample_resume, sample_jd):
    run = run_review_pipeline(sample_resume, sample_jd)
    assert run.provider_name == "rule-based"
    assert any(step.startswith("parse:") for step in run.trace)
    assert any(step.startswith("retrieve:") for step in run.trace)
    assert any(step.startswith("generate:") for step in run.trace)
    assert "critique: schema valid" in run.trace
    assert 0 <= run.result.overall_score <= 100
