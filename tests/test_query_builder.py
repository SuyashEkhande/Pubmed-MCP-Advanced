"""
Tests for query builder utilities.
"""

import pytest
from src.utils.query_builder import QueryBuilder, QueryTerm


class TestQueryBuilder:
    """Tests for E-utilities query builder."""
    
    def test_simple_query(self):
        """Test simple query passthrough."""
        query = QueryBuilder.build_simple_query("cancer")
        assert query == "cancer"
    
    def test_field_query(self):
        """Test field-specific query."""
        query = QueryBuilder.build_field_query("CRISPR", "title")
        assert query == "CRISPR[ti]"
        
        query = QueryBuilder.build_field_query("Zhang F", "author")
        assert query == "Zhang F[au]"
    
    def test_date_range(self):
        """Test date range query."""
        query = QueryBuilder.build_date_range("2020", "2024")
        assert query == "2020:2024[dp]"
        
        query = QueryBuilder.build_date_range("2020", None)
        assert query == "2020:3000[dp]"
        
        query = QueryBuilder.build_date_range(None, None)
        assert query is None
    
    def test_mesh_query(self):
        """Test MeSH query generation."""
        query = QueryBuilder.build_mesh_query("Breast Neoplasms")
        assert query == "Breast Neoplasms[mh]"
        
        query = QueryBuilder.build_mesh_query(
            "Breast Neoplasms",
            qualifiers=["therapy"],
            explode=True
        )
        assert "therapy" in query
    
    def test_mesh_query_no_explode(self):
        """Test MeSH query without explosion."""
        query = QueryBuilder.build_mesh_query("Neoplasms", explode=False)
        assert query == "Neoplasms[mh:noexp]"
    
    def test_boolean_query(self):
        """Test Boolean query building."""
        terms = [
            QueryTerm(term="CRISPR", field="title", operator="AND"),
            QueryTerm(term="gene therapy", field="mesh", operator="AND"),
            QueryTerm(term="review", field="publication_type", operator="AND")
        ]
        
        query = QueryBuilder.build_boolean_query(terms)
        
        assert "CRISPR[ti]" in query
        assert "AND" in query
    
    def test_advanced_query(self):
        """Test advanced query with filters."""
        query = QueryBuilder.build_advanced_query(
            base_query="cancer therapy",
            date_start="2020",
            date_end="2024",
            publication_types=["Review"],
            language="eng",
            free_full_text_only=True
        )
        
        assert "(cancer therapy)" in query
        assert "2020:2024[dp]" in query
        assert "Review[pt]" in query
        assert "eng[la]" in query
        assert "free full text[sb]" in query
    
    def test_author_query(self):
        """Test author query building."""
        query = QueryBuilder.build_author_query("Zhang F")
        assert '"Zhang F"[au]' in query
        
        query = QueryBuilder.build_author_query(
            "Zhang F",
            date_start="2020",
            date_end="2024"
        )
        assert '"Zhang F"[au]' in query
        assert "2020:2024[dp]" in query


class TestQueryValidation:
    """Tests for query validation."""
    
    def test_valid_query(self):
        """Test validation of valid query."""
        result = QueryBuilder.validate_query("cancer AND therapy")
        assert result["valid"] is True
        assert len(result["issues"]) == 0
    
    def test_unbalanced_parentheses(self):
        """Test detection of unbalanced parentheses."""
        result = QueryBuilder.validate_query("(cancer AND therapy")
        assert result["valid"] is False
        assert "Unbalanced parentheses" in result["issues"]
    
    def test_unbalanced_quotes(self):
        """Test detection of unbalanced quotes."""
        result = QueryBuilder.validate_query('"cancer therapy')
        assert result["valid"] is False
        assert "Unbalanced quotes" in result["issues"]
