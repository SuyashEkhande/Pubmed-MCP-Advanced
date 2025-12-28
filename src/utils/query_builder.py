"""
E-utilities query syntax builder.

Converts natural language or structured queries into proper E-utilities syntax.
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from datetime import date
import re


@dataclass
class QueryTerm:
    """A single term in a search query."""
    term: str
    field: Optional[str] = None
    operator: str = "AND"  # AND, OR, NOT


class QueryBuilder:
    """
    Builds E-utilities compatible query strings.
    
    Field tags reference:
    - [ti] = Title
    - [ab] = Abstract
    - [tiab] = Title/Abstract
    - [au] = Author
    - [ta] = Journal title
    - [dp] = Date published (YYYY or YYYY:YYYY)
    - [mh] = MeSH descriptor
    - [tw] = Text words (all fields)
    - [pt] = Publication type
    - [la] = Language
    """
    
    # Field tag mapping
    FIELD_TAGS = {
        "title": "ti",
        "abstract": "ab",
        "title_abstract": "tiab",
        "author": "au",
        "journal": "ta",
        "publication_date": "dp",
        "mesh": "mh",
        "text_words": "tw",
        "publication_type": "pt",
        "language": "la",
        "affiliation": "ad",
        "all_fields": "all",
    }
    
    # Common publication types
    PUBLICATION_TYPES = {
        "review": "Review",
        "clinical_trial": "Clinical Trial",
        "meta_analysis": "Meta-Analysis",
        "systematic_review": "Systematic Review",
        "case_report": "Case Reports",
        "randomized_controlled_trial": "Randomized Controlled Trial",
        "observational_study": "Observational Study",
        "comparative_study": "Comparative Study",
    }
    
    # Language codes
    LANGUAGE_CODES = {
        "english": "eng",
        "spanish": "spa",
        "french": "fre",
        "german": "ger",
        "japanese": "jpn",
        "chinese": "chi",
    }
    
    @classmethod
    def build_simple_query(cls, query: str) -> str:
        """
        Build a simple query, escaping special characters.
        
        Args:
            query: User search query
            
        Returns:
            Properly formatted query string
        """
        # If query contains quoted phrases, preserve them
        if '"' in query:
            return query
        
        # Escape special characters that could break the query
        query = query.strip()
        
        # Wrap multi-word terms without operators in quotes if needed
        return query
    
    @classmethod
    def build_field_query(cls, term: str, field: str) -> str:
        """
        Build a field-specific query.
        
        Args:
            term: Search term
            field: Field name (will be mapped to NCBI field tag)
            
        Returns:
            Field-tagged query string
        """
        field_tag = cls.FIELD_TAGS.get(field.lower(), field)
        return f"{term}[{field_tag}]"
    
    @classmethod
    def build_date_range(
        cls,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        field: str = "dp"
    ) -> Optional[str]:
        """
        Build a date range filter.
        
        Args:
            start_date: Start date (YYYY or YYYY-MM-DD)
            end_date: End date (YYYY or YYYY-MM-DD)
            field: Date field (dp=publication date, edat=entry date)
            
        Returns:
            Date range query string or None
        """
        if not start_date and not end_date:
            return None
        
        # Convert to YYYY format if full date provided
        start = cls._normalize_date(start_date) if start_date else "1800"
        end = cls._normalize_date(end_date) if end_date else "3000"
        
        return f"{start}:{end}[{field}]"
    
    @classmethod
    def _normalize_date(cls, date_str: str) -> str:
        """Normalize date string to YYYY/MM/DD or YYYY format."""
        if re.match(r"^\d{4}$", date_str):
            return date_str
        if re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
            return date_str.replace("-", "/")
        if re.match(r"^\d{4}/\d{2}/\d{2}$", date_str):
            return date_str
        return date_str
    
    @classmethod
    def build_mesh_query(
        cls,
        mesh_term: str,
        qualifiers: Optional[List[str]] = None,
        explode: bool = True
    ) -> str:
        """
        Build a MeSH hierarchy query.
        
        Args:
            mesh_term: MeSH descriptor term
            qualifiers: Optional MeSH qualifiers (e.g., ["therapy", "prevention"])
            explode: Whether to include all subtree terms (default True)
            
        Returns:
            MeSH query string
        """
        tag = "mh" if explode else "mh:noexp"
        
        if qualifiers:
            # Build query with qualifiers
            qual_queries = [f"{mesh_term}/{q}[{tag}]" for q in qualifiers]
            return " OR ".join(qual_queries)
        
        return f"{mesh_term}[{tag}]"
    
    @classmethod
    def build_boolean_query(cls, terms: List[QueryTerm]) -> str:
        """
        Build a complex Boolean query from multiple terms.
        
        Args:
            terms: List of QueryTerm objects
            
        Returns:
            Combined Boolean query string
        """
        if not terms:
            return ""
        
        query_parts = []
        
        for i, qt in enumerate(terms):
            term_str = qt.term
            
            # Add field tag if specified
            if qt.field:
                field_tag = cls.FIELD_TAGS.get(qt.field.lower(), qt.field)
                term_str = f"{qt.term}[{field_tag}]"
            
            # Add operator (except for first term)
            if i > 0 and qt.operator:
                query_parts.append(qt.operator.upper())
            
            query_parts.append(term_str)
        
        return " ".join(query_parts)
    
    @classmethod
    def build_advanced_query(
        cls,
        base_query: str,
        date_start: Optional[str] = None,
        date_end: Optional[str] = None,
        publication_types: Optional[List[str]] = None,
        language: Optional[str] = None,
        free_full_text_only: bool = False,
        open_access_only: bool = False
    ) -> str:
        """
        Build an advanced query with multiple filters.
        
        Args:
            base_query: Main search query
            date_start: Start date for date range filter
            date_end: End date for date range filter
            publication_types: Filter by publication types
            language: Filter by language
            free_full_text_only: Limit to free full text articles
            open_access_only: Limit to open access articles
            
        Returns:
            Complete query string with all filters
        """
        query_parts = [f"({base_query})"]
        
        # Add date range
        date_range = cls.build_date_range(date_start, date_end)
        if date_range:
            query_parts.append(date_range)
        
        # Add publication types
        if publication_types:
            pt_queries = []
            for pt in publication_types:
                pt_mapped = cls.PUBLICATION_TYPES.get(pt.lower(), pt)
                pt_queries.append(f"{pt_mapped}[pt]")
            if len(pt_queries) == 1:
                query_parts.append(pt_queries[0])
            else:
                query_parts.append(f"({' OR '.join(pt_queries)})")
        
        # Add language filter
        if language:
            lang_code = cls.LANGUAGE_CODES.get(language.lower(), language)
            query_parts.append(f"{lang_code}[la]")
        
        # Add free full text filter
        if free_full_text_only:
            query_parts.append("free full text[sb]")
        
        # Add open access filter
        if open_access_only:
            query_parts.append("pubmed pmc open access[sb]")
        
        return " AND ".join(query_parts)
    
    @classmethod
    def build_author_query(
        cls,
        author_name: str,
        date_start: Optional[str] = None,
        date_end: Optional[str] = None
    ) -> str:
        """
        Build an author-centric search query.
        
        Args:
            author_name: Author name (LastName FirstInitial format preferred)
            date_start: Start date for date range
            date_end: End date for date range
            
        Returns:
            Author query string
        """
        # Format author name for search
        author_query = f'"{author_name}"[au]'
        
        if date_start or date_end:
            date_range = cls.build_date_range(date_start, date_end)
            if date_range:
                return f"{author_query} AND {date_range}"
        
        return author_query
    
    @classmethod
    def validate_query(cls, query: str) -> Dict[str, Any]:
        """
        Validate query syntax and provide suggestions.
        
        Args:
            query: Query string to validate
            
        Returns:
            Dictionary with validation results and suggestions
        """
        issues = []
        suggestions = []
        
        # Check for balanced parentheses
        if query.count("(") != query.count(")"):
            issues.append("Unbalanced parentheses")
            suggestions.append("Check that all parentheses are properly closed")
        
        # Check for balanced quotes
        if query.count('"') % 2 != 0:
            issues.append("Unbalanced quotes")
            suggestions.append("Check that all quoted phrases have closing quotes")
        
        # Check for empty field tags
        empty_tags = re.findall(r"\[\s*\]", query)
        if empty_tags:
            issues.append("Empty field tags found")
            suggestions.append("Remove empty brackets or add field names")
        
        # Check for valid boolean operators
        for op in ["AND", "OR", "NOT"]:
            if op.lower() in query or op.capitalize() in query:
                issues.append(f"Boolean operator '{op}' should be uppercase")
                suggestions.append(f"Use '{op.upper()}' for boolean operators")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "suggestions": suggestions,
            "query": query
        }
