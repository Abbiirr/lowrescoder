"""ProgressiveContextLoader - relevance-scored file loader for meta-autocode.

This module implements a file loader that ranks files by relevance to a query,
with test files boosted to appear first. This helps the PIV loop focus on the
most intent-rich files first, reducing environment/context setup failures.
"""
from dataclasses import dataclass
from collections import Counter
from typing import Dict, List


@dataclass
class FileEntry:
    """Represents a file with its relevance score and content."""
    path: str
    score: float
    content: str


class ProgressiveContextLoader:
    """Loads and ranks files by relevance to a query with test file prioritization."""
    
    TEST_BOOST: float = 2.0  # Boost multiplier for test files (> 1.0)
    
    def __init__(self, files: Dict[str, str]):
        """Initialize the loader with a dictionary of file paths to contents.
        
        Args:
            files: Dictionary mapping file paths to their contents
        """
        self.files = files
    
    def rank(self, query: str, token_budget: int = 0) -> List[FileEntry]:
        """Rank files by relevance to the query, with optional token budget truncation.
        
        Args:
            query: Search query to rank files by relevance
            token_budget: If > 0, stop when cumulative character count exceeds
                         token_budget * 4 (approximate chars-per-token)
        
        Returns:
            List of FileEntry objects sorted by score (descending), then path (ascending)
        """
        if not self.files:
            return []
        
        # Calculate scores for all files
        entries = []
        for path, content in self.files.items():
            score = self._calculate_score(query, path, content)
            entries.append(FileEntry(path=path, score=score, content=content))
        
        # Sort by score (descending), then by path (ascending) for stability
        entries.sort(key=lambda e: (-e.score, e.path))
        
        # Apply token budget truncation if specified
        if token_budget > 0:
            max_chars = token_budget * 4
            total_chars = 0
            filtered_entries = []
            
            for entry in entries:
                entry_len = len(entry.content)
                if total_chars + entry_len > max_chars:
                    break
                filtered_entries.append(entry)
                total_chars += entry_len
            
            return filtered_entries
        
        return entries
    
    def _calculate_score(self, query: str, path: str, content: str) -> float:
        """Calculate relevance score for a file based on query overlap.
        
        Uses simple TF-style keyword frequency matching. Test files get boosted.
        
        Args:
            query: Search query terms
            path: File path
            content: File content
        
        Returns:
            Relevance score (higher is more relevant)
        """
        # Boost for test files
        score = 1.0  # Base score
        if "test" in path.lower():
            score *= self.TEST_BOOST
        
        # Calculate query term overlap
        query_terms = self._tokenize(query)
        content_terms = self._tokenize(content)
        
        # Count query term occurrences in content
        query_term_counts = Counter(query_terms)
        content_term_counts = Counter(content_terms)
        
        # Calculate overlap score using TF-IDF style approach
        overlap_score = 0.0
        for term in query_term_counts:
            # Term frequency in content
            tf = content_term_counts.get(term, 0)
            # Inverse document frequency (simplified - assume all files same importance)
            # Just use raw term frequency as the score
            overlap_score += tf
        
        # Normalize by query length to avoid bias
        if query_terms:
            overlap_score /= len(query_terms)
        
        # Combine boost and overlap scores
        final_score = score + overlap_score
        
        return final_score
    
    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenizer that splits text into lowercase words.
        
        Args:
            text: Text to tokenize
        
        Returns:
            List of normalized (lowercase, alphanumeric only) tokens
        """
        # Extract alphanumeric sequences and convert to lowercase
        import re
        return re.findall(r'[a-zA-Z0-9]+', text.lower())
