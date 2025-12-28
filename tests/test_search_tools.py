"""
Tests for Search & Discovery tools.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock


class TestPubMedSearch:
    """Tests for pubmed_search tool."""
    
    @pytest.mark.asyncio
    async def test_basic_search(self):
        """Test basic search returns expected structure."""
        from src.tools.search_tools import pubmed_search
        
        # Mock the EUtilitiesClient
        with patch('src.tools.search_tools.EUtilitiesClient') as MockClient:
            mock_instance = AsyncMock()
            MockClient.return_value.__aenter__.return_value = mock_instance
            
            # Mock search response
            mock_instance.search.return_value = {
                "count": 100,
                "ids": ["12345678", "23456789"],
                "query_translation": "cancer[All Fields]"
            }
            
            # Mock summary response  
            mock_instance.summary.return_value = {
                "results": [
                    {
                        "uid": "12345678",
                        "title": "Test Article 1",
                        "source": "Test Journal",
                        "pubdate": "2024",
                        "authors": []
                    },
                    {
                        "uid": "23456789", 
                        "title": "Test Article 2",
                        "source": "Another Journal",
                        "pubdate": "2024",
                        "authors": []
                    }
                ]
            }
            
            result = await pubmed_search(
                query="cancer",
                max_results=10
            )
            
            assert "total_results" in result
            assert "results" in result
            assert result["total_results"] == 100
            assert len(result["results"]) == 2
    
    @pytest.mark.asyncio
    async def test_search_with_filters(self):
        """Test search with filters is applied correctly."""
        from src.tools.search_tools import pubmed_search
        
        with patch('src.tools.search_tools.EUtilitiesClient') as MockClient:
            mock_instance = AsyncMock()
            MockClient.return_value.__aenter__.return_value = mock_instance
            
            mock_instance.search.return_value = {
                "count": 50,
                "ids": ["11111111"],
                "query_translation": "(cancer) AND 2023:2024[dp]"
            }
            mock_instance.summary.return_value = {"results": []}
            
            result = await pubmed_search(
                query="cancer",
                filters={
                    "publication_date_start": "2023",
                    "publication_date_end": "2024",
                    "publication_types": ["Review"]
                },
                max_results=10
            )
            
            assert "total_results" in result
            mock_instance.search.assert_called_once()


class TestMeSHSearch:
    """Tests for mesh_term_search tool."""
    
    @pytest.mark.asyncio
    async def test_mesh_search_basic(self):
        """Test MeSH search returns expected structure."""
        from src.tools.search_tools import mesh_term_search
        
        with patch('src.tools.search_tools.EUtilitiesClient') as MockClient:
            mock_instance = AsyncMock()
            MockClient.return_value.__aenter__.return_value = mock_instance
            
            mock_instance.search.return_value = {
                "count": 5000,
                "ids": ["11111111"],
                "query_translation": "Breast Neoplasms[mh]"
            }
            mock_instance.summary.return_value = {"results": []}
            
            result = await mesh_term_search(
                mesh_term="Breast Neoplasms",
                qualifiers=["therapy"],
                max_results=10
            )
            
            assert "mesh_descriptor" in result
            assert result["mesh_descriptor"]["heading"] == "Breast Neoplasms"
            assert "total_results" in result


class TestGlobalSearch:
    """Tests for global_search tool."""
    
    @pytest.mark.asyncio
    async def test_global_search(self):
        """Test global search returns database counts."""
        from src.tools.search_tools import global_search
        
        with patch('src.tools.search_tools.EUtilitiesClient') as MockClient:
            mock_instance = AsyncMock()
            MockClient.return_value.__aenter__.return_value = mock_instance
            
            mock_instance.gquery.return_value = {
                "databases": [
                    {"db_name": "pubmed", "menu_name": "PubMed", "count": 1000, "status": "ok"},
                    {"db_name": "pmc", "menu_name": "PMC", "count": 500, "status": "ok"},
                    {"db_name": "gene", "menu_name": "Gene", "count": 50, "status": "ok"}
                ]
            }
            
            result = await global_search(query="BRCA1")
            
            assert "databases" in result
            assert "total_across_databases" in result
            assert result["total_across_databases"] == 1550
