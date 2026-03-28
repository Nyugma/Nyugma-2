"""
Unit tests for ChromaDBClient.
"""

import pytest
from unittest.mock import patch, MagicMock

from src.components.chromadb_client import ChromaDBClient, QueryResult


class TestQueryResult:
    """Tests for the QueryResult dataclass."""

    def test_default_empty(self):
        result = QueryResult()
        assert result.documents == []
        assert result.metadatas == []
        assert result.distances == []

    def test_with_data(self):
        result = QueryResult(
            documents=["doc1", "doc2"],
            metadatas=[{"id": "1"}, {"id": "2"}],
            distances=[0.1, 0.2],
        )
        assert result.documents == ["doc1", "doc2"]
        assert len(result.metadatas) == 2
        assert result.distances == [0.1, 0.2]


class TestChromaDBClient:
    """Tests for ChromaDBClient."""

    @patch("src.components.chromadb_client.chromadb")
    def test_init_connects_to_persistent_client(self, mock_chromadb):
        mock_client = MagicMock()
        mock_chromadb.PersistentClient.return_value = mock_client

        client = ChromaDBClient(persist_directory="/tmp/test_chromadb")

        mock_chromadb.PersistentClient.assert_called_once_with(path="/tmp/test_chromadb")
        mock_client.get_or_create_collection.assert_called_once_with("legal_cases")

    @patch("src.components.chromadb_client.chromadb")
    def test_init_uses_settings_default(self, mock_chromadb):
        mock_client = MagicMock()
        mock_chromadb.PersistentClient.return_value = mock_client

        with patch("src.components.chromadb_client.settings") as mock_settings:
            mock_settings.CHROMADB_DIR = "/default/chromadb"
            client = ChromaDBClient()

        mock_chromadb.PersistentClient.assert_called_once_with(path="/default/chromadb")

    @patch("src.components.chromadb_client.chromadb")
    def test_init_raises_on_connection_failure(self, mock_chromadb):
        mock_chromadb.PersistentClient.side_effect = Exception("Connection failed")

        with pytest.raises(Exception, match="Connection failed"):
            ChromaDBClient(persist_directory="/bad/path")

    @patch("src.components.chromadb_client.chromadb")
    def test_query_returns_query_result(self, mock_chromadb):
        mock_collection = MagicMock()
        mock_collection.query.return_value = {
            "documents": [["doc1", "doc2"]],
            "metadatas": [[{"case_id": "1"}, {"case_id": "2"}]],
            "distances": [[0.1, 0.5]],
        }
        mock_client = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_chromadb.PersistentClient.return_value = mock_client

        client = ChromaDBClient(persist_directory="/tmp/test")
        result = client.query("contract dispute", n_results=2)

        assert isinstance(result, QueryResult)
        assert result.documents == ["doc1", "doc2"]
        assert result.metadatas == [{"case_id": "1"}, {"case_id": "2"}]
        assert result.distances == [0.1, 0.5]
        mock_collection.query.assert_called_once_with(
            query_texts=["contract dispute"], n_results=2
        )

    @patch("src.components.chromadb_client.chromadb")
    def test_query_handles_empty_results(self, mock_chromadb):
        mock_collection = MagicMock()
        mock_collection.query.return_value = {
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]],
        }
        mock_client = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_chromadb.PersistentClient.return_value = mock_client

        client = ChromaDBClient(persist_directory="/tmp/test")
        result = client.query("nonexistent topic")

        assert result.documents == []
        assert result.metadatas == []
        assert result.distances == []

    @patch("src.components.chromadb_client.chromadb")
    def test_query_raises_on_failure(self, mock_chromadb):
        mock_collection = MagicMock()
        mock_collection.query.side_effect = Exception("Query failed")
        mock_client = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_chromadb.PersistentClient.return_value = mock_client

        client = ChromaDBClient(persist_directory="/tmp/test")

        with pytest.raises(Exception, match="Query failed"):
            client.query("test query")

    @patch("src.components.chromadb_client.chromadb")
    def test_query_default_n_results(self, mock_chromadb):
        mock_collection = MagicMock()
        mock_collection.query.return_value = {
            "documents": [["a", "b", "c", "d", "e"]],
            "metadatas": [[{}, {}, {}, {}, {}]],
            "distances": [[0.1, 0.2, 0.3, 0.4, 0.5]],
        }
        mock_client = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_chromadb.PersistentClient.return_value = mock_client

        client = ChromaDBClient(persist_directory="/tmp/test")
        client.query("test")

        mock_collection.query.assert_called_once_with(
            query_texts=["test"], n_results=5
        )
