import pytest
import json
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from src.super_executor import SuperExecutor


@pytest.fixture
def super_executor():
    with patch.dict('os.environ', {'SUPER_BINARY_PATH': '/opt/bin/super'}):
        return SuperExecutor()


class TestSuperExecutor:
    """Test super binary execution functionality."""
    
    @pytest.mark.asyncio
    async def test_execute_query_success(self, super_executor):
        """Test successful query execution."""
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = (
            b'{"id": 1, "name": "test"}\n{"id": 2, "name": "test2"}\n',
            b''
        )
        
        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            with patch('asyncio.wait_for', side_effect=lambda coro, timeout: coro):
                result = await super_executor.execute_query(
                    "FROM 's3://test/data' | HEAD 10",
                    "s3://test/data"
                )
        
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["id"] == 1
        assert result[1]["name"] == "test2"
    
    @pytest.mark.asyncio
    async def test_execute_query_failure(self, super_executor):
        """Test query execution failure."""
        mock_process = AsyncMock()
        mock_process.returncode = 1
        mock_process.communicate.return_value = (b'', b'Error: Invalid query')
        
        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            with patch('asyncio.wait_for', side_effect=lambda coro, timeout: coro):
                with pytest.raises(RuntimeError) as exc_info:
                    await super_executor.execute_query(
                        "INVALID QUERY",
                        "s3://test/data"
                    )
        
        assert "Super query failed" in str(exc_info.value)
        assert "Invalid query" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_execute_query_timeout(self, super_executor):
        """Test query execution timeout."""
        mock_process = AsyncMock()
        mock_process.kill = MagicMock()
        mock_process.wait = AsyncMock()
        
        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            with patch('asyncio.wait_for', side_effect=asyncio.TimeoutError):
                with pytest.raises(RuntimeError) as exc_info:
                    await super_executor.execute_query(
                        "FROM 's3://test/data' | HEAD 10",
                        "s3://test/data"
                    )
        
        assert "Query timeout" in str(exc_info.value)
        mock_process.kill.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_query_binary_not_found(self, super_executor):
        """Test handling when super binary is not found."""
        with patch('asyncio.create_subprocess_exec', side_effect=FileNotFoundError):
            with pytest.raises(RuntimeError) as exc_info:
                await super_executor.execute_query(
                    "FROM 's3://test/data' | HEAD 10",
                    "s3://test/data"
                )
        
        assert "Super binary not found" in str(exc_info.value)
    
    def test_parse_super_output(self, super_executor):
        """Test parsing super JSON output."""
        output = '{"id": 1, "name": "test1"}\n{"id": 2, "name": "test2"}\n'
        result = super_executor._parse_super_output(output)
        
        assert len(result) == 2
        assert result[0]["id"] == 1
        assert result[1]["name"] == "test2"
    
    def test_parse_super_output_malformed(self, super_executor):
        """Test parsing malformed JSON output."""
        output = '{"id": 1, "name": "test1"}\n{"invalid": json}\n{"id": 2, "name": "test2"}\n'
        result = super_executor._parse_super_output(output)
        
        # Should skip malformed JSON and continue
        assert len(result) == 2
        assert result[0]["id"] == 1
        assert result[1]["id"] == 2
    
    def test_parse_super_output_empty(self, super_executor):
        """Test parsing empty output."""
        output = ''
        result = super_executor._parse_super_output(output)
        
        assert result == []
    
    def test_get_process_env(self, super_executor):
        """Test environment variable setup for super process."""
        with patch.dict('os.environ', {
            'AWS_ACCESS_KEY_ID': 'test-key',
            'AWS_SECRET_ACCESS_KEY': 'test-secret',
            'AWS_REGION': 'us-west-2'
        }):
            env = super_executor._get_process_env()
        
        assert env['AWS_ACCESS_KEY_ID'] == 'test-key'
        assert env['AWS_SECRET_ACCESS_KEY'] == 'test-secret'
        assert env['AWS_REGION'] == 'us-west-2'
    
    def test_get_process_env_default_region(self, super_executor):
        """Test default AWS region setting."""
        with patch.dict('os.environ', {}, clear=True):
            env = super_executor._get_process_env()
        
        assert env['AWS_REGION'] == 'us-east-1'
    
    @pytest.mark.asyncio
    async def test_test_super_binary_success(self, super_executor):
        """Test super binary validation success."""
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = (b'super version 1.0.0\n', b'')
        
        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            with patch('asyncio.wait_for', side_effect=lambda coro, timeout: coro):
                result = await super_executor.test_super_binary()
        
        assert result["status"] == "success"
        assert result["accessible"] is True
        assert "super version 1.0.0" in result["version"]
    
    @pytest.mark.asyncio
    async def test_test_super_binary_failure(self, super_executor):
        """Test super binary validation failure."""
        mock_process = AsyncMock()
        mock_process.returncode = 1
        mock_process.communicate.return_value = (b'', b'Command not found')
        
        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            with patch('asyncio.wait_for', side_effect=lambda coro, timeout: coro):
                result = await super_executor.test_super_binary()
        
        assert result["status"] == "error"
        assert result["accessible"] is False
        assert "Command not found" in result["error"]
    
    @pytest.mark.asyncio
    async def test_test_super_binary_not_found(self, super_executor):
        """Test super binary not found."""
        with patch('asyncio.create_subprocess_exec', side_effect=FileNotFoundError):
            result = await super_executor.test_super_binary()
        
        assert result["status"] == "error"
        assert result["accessible"] is False
        assert "Super binary not found" in result["error"]
    
    @pytest.mark.asyncio
    async def test_validate_s3_access_success(self, super_executor):
        """Test S3 access validation success."""
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = (b'{"test": "data"}\n', b'')
        
        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            with patch('asyncio.wait_for', side_effect=lambda coro, timeout: coro):
                result = await super_executor.validate_s3_access("s3://test-bucket/data")
        
        assert result["status"] == "success"
        assert result["accessible"] is True
        assert result["s3_path"] == "s3://test-bucket/data"
    
    @pytest.mark.asyncio
    async def test_validate_s3_access_failure(self, super_executor):
        """Test S3 access validation failure."""
        mock_process = AsyncMock()
        mock_process.returncode = 1
        mock_process.communicate.return_value = (b'', b'Access denied')
        
        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            with patch('asyncio.wait_for', side_effect=lambda coro, timeout: coro):
                result = await super_executor.validate_s3_access("s3://test-bucket/data")
        
        assert result["status"] == "error"
        assert result["accessible"] is False
        assert "Access denied" in result["error"]
    
    def test_format_results_for_display(self, super_executor):
        """Test result formatting for display."""
        results = [
            {"id": 1, "name": "John", "revenue": 1000},
            {"id": 2, "name": "Jane", "revenue": 2000}
        ]
        
        formatted = super_executor.format_results_for_display(results)
        
        assert "id" in formatted
        assert "name" in formatted
        assert "revenue" in formatted
        assert "John" in formatted
        assert "Jane" in formatted
        assert "|" in formatted  # Table format
    
    def test_format_results_for_display_empty(self, super_executor):
        """Test formatting empty results."""
        results = []
        formatted = super_executor.format_results_for_display(results)
        
        assert formatted == "No results found."
    
    def test_get_query_statistics(self, super_executor):
        """Test query statistics generation."""
        results = [
            {"id": 1, "name": "John"},
            {"id": 2, "name": "Jane"}
        ]
        
        stats = super_executor.get_query_statistics(results)
        
        assert stats["total_records"] == 2
        assert stats["fields"] == ["id", "name"]
        assert stats["field_count"] == 2
        assert "truncated" in stats
    
    def test_get_query_statistics_empty(self, super_executor):
        """Test statistics for empty results."""
        results = []
        stats = super_executor.get_query_statistics(results)
        
        assert stats["total_records"] == 0
        assert stats["fields"] == []