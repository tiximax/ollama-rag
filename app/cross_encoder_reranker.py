"""
🎯 Cross-Encoder Reranker - Alternative reranking với higher quality!

Cross-encoders xử lý (query, document) pairs trực tiếp, cho kết quả chính xác hơn
bi-encoders nhưng chậm hơn. Ideal cho small result sets (top 10-20).

Comparison:
- **BGE Reranker (Bi-encoder)**: Fast, good for large sets (100+ docs)
- **Cross-Encoder**: Slower, better quality for small sets (10-20 docs)

Models supported:
- cross-encoder/ms-marco-MiniLM-L-6-v2 (lightweight, ~80MB)
- cross-encoder/ms-marco-MiniLM-L-12-v2 (better quality, ~140MB)
- cross-encoder/ms-marco-TinyBERT-L-2-v2 (very fast, ~20MB)

Features:
- ✅ Higher reranking quality than bi-encoders
- ✅ Direct (query, doc) scoring
- ✅ Multiple model options
- ✅ Batch processing
- ✅ Configurable top-k
- ✅ Fallback to simple reranker
"""

import logging
import time
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


class CrossEncoderReranker:
    """
    🎯 Cross-Encoder Reranker - High-quality document reranking!
    
    Cross-encoders process (query, document) pairs together, giving better
    relevance scores than bi-encoders that encode separately.
    
    Usage:
        >>> reranker = CrossEncoderReranker(model="cross-encoder/ms-marco-MiniLM-L-6-v2")
        >>> 
        >>> # Rerank top 10 documents
        >>> docs, scores = reranker.rerank(
        ...     query="What is RAG?",
        ...     docs=["RAG is...", "Retrieval means...", ...],
        ...     top_k=5
        ... )
        >>> # Returns top 5 best matches according to cross-encoder
    
    Performance:
        - 10 docs: ~100-200ms (MiniLM-L-6)
        - 20 docs: ~200-400ms (MiniLM-L-6)
        - 50 docs: ~500-1000ms (not recommended)
    
    Quality:
        - More accurate than BGE reranker for small sets
        - Better at understanding query-document semantic relationship
        - Ideal for final reranking of top candidates
    """
    
    def __init__(
        self,
        model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        device: str = "cpu",
        batch_size: int = 16,
    ):
        """
        Args:
            model: HuggingFace cross-encoder model name
                   - ms-marco-MiniLM-L-6-v2: Fast, good quality (recommended)
                   - ms-marco-MiniLM-L-12-v2: Better quality, slower
                   - ms-marco-TinyBERT-L-2-v2: Fastest, lower quality
            device: Device to run on ("cpu" or "cuda")
            batch_size: Batch size for scoring pairs
        """
        self.model_name = model
        self.device = device
        self.batch_size = batch_size
        self.model: Optional[Any] = None
        self._initialized = False
        
        # Try to load model
        self._load_model()
    
    def _load_model(self) -> bool:
        """
        Load cross-encoder model from sentence-transformers.
        
        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            from sentence_transformers import CrossEncoder
            
            logger.info(f"Loading cross-encoder model: {self.model_name}")
            start = time.time()
            
            self.model = CrossEncoder(
                self.model_name,
                device=self.device,
                max_length=512,  # Max input length
            )
            
            duration = time.time() - start
            logger.info(f"✅ Cross-encoder loaded in {duration:.2f}s")
            self._initialized = True
            return True
        
        except ImportError:
            logger.warning(
                "⚠️ sentence-transformers not installed. "
                "Install: pip install sentence-transformers"
            )
            self._initialized = False
            return False
        
        except Exception as e:
            logger.error(f"❌ Failed to load cross-encoder: {e}")
            self._initialized = False
            return False
    
    def is_available(self) -> bool:
        """Check if reranker is available."""
        return self._initialized and self.model is not None
    
    def rerank(
        self,
        query: str,
        docs: List[str],
        metas: Optional[List[Dict[str, Any]]] = None,
        top_k: int = 10,
        return_scores: bool = True,
    ) -> Tuple[List[str], List[Dict[str, Any]], Optional[List[float]]]:
        """
        Rerank documents using cross-encoder.
        
        Args:
            query: Query string
            docs: List of document strings to rerank
            metas: Optional list of metadata dicts
            top_k: Number of top documents to return
            return_scores: Whether to return relevance scores
        
        Returns:
            Tuple of (reranked_docs, reranked_metas, scores)
        """
        if not self.is_available():
            logger.warning("Cross-encoder not available, returning original order")
            scores = None if not return_scores else [1.0] * min(top_k, len(docs))
            return (
                docs[:top_k],
                metas[:top_k] if metas else [{}] * min(top_k, len(docs)),
                scores,
            )
        
        if not docs:
            return [], [], []
        
        # Handle metas
        if metas is None:
            metas = [{}] * len(docs)
        
        try:
            start_time = time.time()
            
            # Create (query, doc) pairs
            pairs = [[query, doc] for doc in docs]
            
            # Score all pairs using cross-encoder
            scores = self.model.predict(
                pairs,
                batch_size=self.batch_size,
                show_progress_bar=False,
                convert_to_numpy=True,
            )
            
            # Convert to list if numpy array
            if isinstance(scores, np.ndarray):
                scores = scores.tolist()
            
            duration_ms = (time.time() - start_time) * 1000
            
            # Sort by scores (descending)
            sorted_indices = sorted(
                range(len(scores)),
                key=lambda i: scores[i],
                reverse=True,
            )[:top_k]
            
            # Reorder docs, metas, scores
            reranked_docs = [docs[i] for i in sorted_indices]
            reranked_metas = [metas[i] for i in sorted_indices]
            reranked_scores = [scores[i] for i in sorted_indices] if return_scores else None
            
            logger.debug(
                f"Cross-encoder reranked {len(docs)} docs to top {top_k} in {duration_ms:.0f}ms"
            )
            
            return reranked_docs, reranked_metas, reranked_scores
        
        except Exception as e:
            logger.error(f"Cross-encoder reranking failed: {e}")
            # Fallback: return original order
            scores = None if not return_scores else [1.0] * min(top_k, len(docs))
            return docs[:top_k], metas[:top_k], scores
    
    def compare_with_baseline(
        self,
        query: str,
        docs: List[str],
        baseline_scores: List[float],
        top_k: int = 10,
    ) -> Dict[str, Any]:
        """
        Compare cross-encoder reranking with baseline scores.
        
        Useful for A/B testing and quality assessment.
        
        Args:
            query: Query string
            docs: Documents
            baseline_scores: Baseline relevance scores (e.g., from vector search)
            top_k: Number of top documents
        
        Returns:
            Comparison dict with metrics
        """
        if not self.is_available():
            return {"error": "Cross-encoder not available"}
        
        # Get baseline top-k
        baseline_indices = sorted(
            range(len(baseline_scores)),
            key=lambda i: baseline_scores[i],
            reverse=True,
        )[:top_k]
        
        # Rerank with cross-encoder
        _, _, ce_scores = self.rerank(query, docs, top_k=len(docs), return_scores=True)
        
        if ce_scores is None:
            return {"error": "Cross-encoder scoring failed"}
        
        # Get cross-encoder top-k
        ce_indices = sorted(
            range(len(ce_scores)),
            key=lambda i: ce_scores[i],
            reverse=True,
        )[:top_k]
        
        # Calculate overlap
        overlap = len(set(baseline_indices) & set(ce_indices))
        overlap_pct = (overlap / top_k) * 100 if top_k > 0 else 0
        
        # Calculate rank correlation (Spearman)
        try:
            from scipy.stats import spearmanr
            correlation, _ = spearmanr(baseline_scores, ce_scores)
        except ImportError:
            correlation = None
        
        # Score improvement (average score change for top-k)
        baseline_top_scores = [baseline_scores[i] for i in baseline_indices]
        ce_top_scores = [ce_scores[i] for i in ce_indices]
        
        avg_baseline = sum(baseline_top_scores) / len(baseline_top_scores)
        avg_ce = sum(ce_top_scores) / len(ce_top_scores)
        score_improvement = ((avg_ce - avg_baseline) / avg_baseline) * 100 if avg_baseline != 0 else 0
        
        return {
            "top_k": top_k,
            "overlap": overlap,
            "overlap_percentage": overlap_pct,
            "rank_correlation": correlation,
            "avg_baseline_score": avg_baseline,
            "avg_ce_score": avg_ce,
            "score_improvement_pct": score_improvement,
            "baseline_top_indices": baseline_indices,
            "ce_top_indices": ce_indices,
        }
    
    def __repr__(self) -> str:
        status = "✅ Ready" if self.is_available() else "❌ Not available"
        return (
            f"CrossEncoderReranker(model={self.model_name}, "
            f"device={self.device}, status={status})"
        )


# Example usage and testing
if __name__ == "__main__":
    import sys
    
    logging.basicConfig(level=logging.INFO)
    
    print("🧪 Testing Cross-Encoder Reranker...\n")
    
    # Test 1: Model loading
    print("Test 1: Loading model...")
    reranker = CrossEncoderReranker(model="cross-encoder/ms-marco-MiniLM-L-6-v2")
    print(f"Status: {reranker}\n")
    
    if not reranker.is_available():
        print("⚠️ Cross-encoder not available. Install: pip install sentence-transformers")
        print("Exiting test...")
        sys.exit(0)
    
    # Test 2: Basic reranking
    print("Test 2: Basic reranking...")
    query = "What is machine learning?"
    docs = [
        "Machine learning is a subset of AI that enables systems to learn from data.",
        "Python is a popular programming language.",
        "Deep learning uses neural networks with multiple layers.",
        "The weather today is sunny and warm.",
        "Supervised learning requires labeled training data.",
    ]
    
    reranked_docs, _, scores = reranker.rerank(query, docs, top_k=3)
    
    print(f"Query: {query}")
    print(f"\nTop 3 reranked documents:")
    for i, (doc, score) in enumerate(zip(reranked_docs, scores or []), 1):
        print(f"  {i}. Score: {score:.4f} - {doc[:60]}...")
    
    # Test 3: Performance
    print("\n\nTest 3: Performance benchmark...")
    n_docs = 20
    large_docs = [f"Document {i} about various topics" for i in range(n_docs)]
    
    start = time.time()
    _, _, _ = reranker.rerank(query, large_docs, top_k=10)
    duration_ms = (time.time() - start) * 1000
    
    print(f"Reranked {n_docs} documents in {duration_ms:.0f}ms")
    print(f"Throughput: {n_docs / (duration_ms / 1000):.1f} docs/sec")
    
    # Test 4: Comparison with baseline
    print("\n\nTest 4: Comparison with baseline scores...")
    baseline_scores = [0.8, 0.3, 0.7, 0.1, 0.6]  # Simulated vector search scores
    
    comparison = reranker.compare_with_baseline(query, docs, baseline_scores, top_k=3)
    
    print(f"Overlap with baseline top-3: {comparison['overlap']}/3 ({comparison['overlap_percentage']:.1f}%)")
    if comparison.get('rank_correlation') is not None:
        print(f"Rank correlation: {comparison['rank_correlation']:.3f}")
    print(f"Score improvement: {comparison['score_improvement_pct']:+.1f}%")
    
    print("\n✅ Cross-Encoder Reranker test completed!")
