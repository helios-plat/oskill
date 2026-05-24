import sys
from unittest.mock import MagicMock, patch
sys.modules["docker"] = MagicMock()
sys.modules["docker.errors"] = MagicMock()

import pytest
from oskill.retrieve_and_synthesize import retrieve_and_synthesize, SynthesizedResult, RetrievedDoc

def test_retrieve_and_synthesize_success():
    """Test successful retrieval and synthesis."""
    mock_llm = MagicMock()
    mock_llm.return_value = {"content": "The root cause is a database deadlock. Confidence: 0.9"}
    
    def mock_search(query, corpus_id, top_k):
        return [
            RetrievedDoc(doc_id="D1", content="Deadlock observed in logs", score=0.95),
            RetrievedDoc(doc_id="D2", content="Database retry failed", score=0.8)
        ]
        
    result = retrieve_and_synthesize(
        query="database error",
        corpus_id="incidents",
        llm=mock_llm,
        vector_search_fn=mock_search
    )
    
    assert result.confidence == 0.9
    assert len(result.retrieved_docs) == 2
    assert "database deadlock" in result.synthesized_answer

def test_retrieve_and_synthesize_no_docs():
    """Test when no documents are found."""
    mock_llm = MagicMock()
    def mock_search(query, corpus_id, top_k):
        return []
        
    result = retrieve_and_synthesize(
        query="missing topic",
        corpus_id="empty_corpus",
        llm=mock_llm,
        vector_search_fn=mock_search
    )
    
    assert result.confidence == 0.0
    assert result.synthesized_answer == "No relevant documents found."
    assert len(result.retrieved_docs) == 0

def test_retrieve_and_synthesize_no_search_fn():
    """Test error when search function is missing."""
    mock_llm = MagicMock()
    with pytest.raises(ValueError, match="vector_search_fn must be provided"):
        retrieve_and_synthesize(query="test", corpus_id="c1", llm=mock_llm)

def test_retrieve_and_synthesize_llm_failure():
    """Test LLM failure handling."""
    mock_llm = MagicMock(side_effect=Exception("LLM Error"))
    def mock_search(query, corpus_id, top_k):
        return [RetrievedDoc(doc_id="1", content="test", score=1.0)]
        
    with pytest.raises(Exception, match="LLM Error"):
        retrieve_and_synthesize(query="test", corpus_id="c1", llm=mock_llm, vector_search_fn=mock_search)

def test_retrieve_and_synthesize_low_confidence():
    """Test when LLM returns low confidence or no confidence mentioned."""
    mock_llm = MagicMock()
    mock_llm.return_value = {"content": "I am not sure what is happening."}
    
    def mock_search(query, corpus_id, top_k):
        return [RetrievedDoc(doc_id="1", content="vague evidence", score=0.5)]
        
    result = retrieve_and_synthesize(
        query="vague query",
        corpus_id="c1",
        llm=mock_llm,
        vector_search_fn=mock_search
    )
    
    assert result.confidence == 0.5 # Default fallback

def test_retrieve_and_synthesize_top_k():
    """Test respecting top_k parameter."""
    mock_llm = MagicMock()
    mock_llm.return_value = {"content": "Done"}
    
    def mock_search(query, corpus_id, top_k):
        assert top_k == 3
        return [RetrievedDoc(doc_id="1", content="t", score=1.0)] * top_k
        
    retrieve_and_synthesize(query="q", corpus_id="c", llm=mock_llm, vector_search_fn=mock_search, top_k=3)

def test_retrieve_and_synthesize_empty_query():
    """Test empty query."""
    mock_llm = MagicMock()
    mock_llm.return_value = {"content": "Empty result"}
    def mock_search(query, corpus_id, top_k):
        return []
    result = retrieve_and_synthesize(query="", corpus_id="c", llm=mock_llm, vector_search_fn=mock_search)
    assert result.synthesized_answer == "No relevant documents found."

def test_retrieve_and_synthesize_complex_content():
    """Test handling complex content strings."""
    mock_llm = MagicMock()
    mock_llm.return_value = {"content": "Answer with quotes \"quoted\" and newlines\n\nConfidence: 1.0"}
    
    def mock_search(query, corpus_id, top_k):
        return [RetrievedDoc(doc_id="1", content="Complex content \n with \t chars", score=1.0)]
        
    result = retrieve_and_synthesize(query="q", corpus_id="c", llm=mock_llm, vector_search_fn=mock_search)
    assert result.confidence == 1.0
