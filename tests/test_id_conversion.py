"""
Tests for ID Conversion tools.
"""

import pytest
from unittest.mock import AsyncMock, patch


class TestConvertArticleIds:
    """Tests for convert_article_ids tool."""
    
    @pytest.mark.asyncio
    async def test_batch_conversion(self):
        """Test batch ID conversion."""
        from src.tools.id_conversion_tools import convert_article_ids
        
        with patch('src.tools.id_conversion_tools.IDConverterClient') as MockClient:
            mock_instance = AsyncMock()
            MockClient.return_value.__aenter__.return_value = mock_instance
            
            mock_instance.convert_ids.return_value = {
                "total_requested": 2,
                "successful": 2,
                "failed_count": 0,
                "conversions": [
                    {
                        "requested_id": "37000000",
                        "pmid": "37000000",
                        "pmcid": "PMC1234567",
                        "doi": "10.1000/test"
                    },
                    {
                        "requested_id": "37000001",
                        "pmid": "37000001",
                        "pmcid": None,
                        "doi": "10.1000/test2"
                    }
                ],
                "failed": []
            }
            
            result = await convert_article_ids(
                ids=["37000000", "37000001"],
                from_type="pmid"
            )
            
            assert result["total_requested"] == 2
            assert result["successful"] == 2
            assert len(result["conversions"]) == 2


class TestResolveIdentifier:
    """Tests for resolve_article_identifier tool."""
    
    @pytest.mark.asyncio
    async def test_resolve_doi(self):
        """Test resolving a DOI."""
        from src.tools.id_conversion_tools import resolve_article_identifier
        
        with patch('src.tools.id_conversion_tools.IDConverterClient') as MockClient:
            mock_instance = AsyncMock()
            MockClient.return_value.__aenter__.return_value = mock_instance
            
            mock_instance.detect_id_type.return_value = "doi"
            mock_instance.resolve_id.return_value = {
                "requested_id": "10.1038/nature12373",
                "pmid": "23903654",
                "pmcid": "PMC3749474",
                "doi": "10.1038/nature12373"
            }
            
            result = await resolve_article_identifier(
                identifier="10.1038/nature12373"
            )
            
            assert result["pmid"] == "23903654"
            assert result["pmcid"] == "PMC3749474"


class TestIDTypeDetection:
    """Tests for ID type detection."""
    
    def test_detect_pmid(self):
        """Test PMID detection."""
        from src.clients.id_converter import IDConverterClient
        
        assert IDConverterClient.detect_id_type("37000000") == "pmid"
        assert IDConverterClient.detect_id_type("12345") == "pmid"
    
    def test_detect_pmcid(self):
        """Test PMCID detection."""
        from src.clients.id_converter import IDConverterClient
        
        assert IDConverterClient.detect_id_type("PMC7611378") == "pmcid"
        assert IDConverterClient.detect_id_type("pmc1234567") == "pmcid"
    
    def test_detect_doi(self):
        """Test DOI detection."""
        from src.clients.id_converter import IDConverterClient
        
        assert IDConverterClient.detect_id_type("10.1038/nature12373") == "doi"
        assert IDConverterClient.detect_id_type("10.1093/nar/gks1195") == "doi"
    
    def test_detect_manuscript_id(self):
        """Test Manuscript ID detection."""
        from src.clients.id_converter import IDConverterClient
        
        assert IDConverterClient.detect_id_type("NIHMS1677310") == "mid"
