import pytest
import json
from unittest.mock import patch, AsyncMock, MagicMock
from src.mcp_server import (
    QueryS3DataRequest, 
    ExploreS3DataRequest, 
    ListS3FilesRequest,
    validate_super_binary,
    query_s3_data,
    explore_s3_data,
    list_s3_files,
    lambda_handler
)


class TestMCPServer:
    """Test MCP server functionality and tools."""
    
    def test_validate_super_binary_success(self):
        """Test successful super binary validation."""
        with patch('os.path.exists', return_value=True):
            with patch('os.access', return_value=True):
                with patch.dict('os.environ', {'SUPER_BINARY_PATH': '/opt/bin/super'}):
                    # Should not raise an exception
                    validate_super_binary()
    
    def test_validate_super_binary_not_found(self):
        """Test super binary not found."""
        with patch('os.path.exists', return_value=False):
            with patch.dict('os.environ', {'SUPER_BINARY_PATH': '/opt/bin/super'}):
                with pytest.raises(RuntimeError) as exc_info:
                    validate_super_binary()
                assert "Super binary not found" in str(exc_info.value)
    
    def test_validate_super_binary_not_executable(self):
        """Test super binary not executable."""
        with patch('os.path.exists', return_value=True):
            with patch('os.access', return_value=False):
                with patch.dict('os.environ', {'SUPER_BINARY_PATH': '/opt/bin/super'}):
                    with pytest.raises(RuntimeError) as exc_info:
                        validate_super_binary()
                    assert "not executable" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_query_s3_data_success(self):
        """Test successful S3 data query."""
        request = QueryS3DataRequest(
            request="top 10 customers by revenue",
            s3_path="s3://test-bucket/sales/*",
            limit=10
        )
        
        mock_query = "FROM 's3://test-bucket/sales/*' | SUMMARIZE sum(revenue) BY customer | ORDER BY sum(revenue) DESC | HEAD 10"
        mock_results = [
            {"customer": "John", "sum_revenue": 1000},
            {"customer": "Jane", "sum_revenue": 800}
        ]
        
        with patch('src.mcp_server.query_processor') as mock_processor:
            with patch('src.mcp_server.super_executor') as mock_executor:
                mock_processor.process_query.return_value = mock_query
                mock_executor.execute_query.return_value = mock_results
                
                result = await query_s3_data(request)
        
        assert result["status"] == "success"
        assert result["query"] == mock_query
        assert result["results"] == mock_results
        assert result["record_count"] == 2
    
    @pytest.mark.asyncio
    async def test_query_s3_data_failure(self):
        """Test S3 data query failure."""
        request = QueryS3DataRequest(
            request="invalid query",
            s3_path="s3://test-bucket/data/*"
        )
        
        with patch('src.mcp_server.query_processor') as mock_processor:
            mock_processor.process_query.side_effect = Exception("Query processing failed")
            
            result = await query_s3_data(request)
        
        assert result["status"] == "error"
        assert "Query processing failed" in result["error"]
        assert result["query"] == "invalid query"
    
    @pytest.mark.asyncio
    async def test_explore_s3_data_success(self):
        """Test successful S3 data exploration."""
        request = ExploreS3DataRequest(
            s3_path="s3://test-bucket/data/*",
            sample_size=100
        )
        
        mock_sample_data = [
            {"id": 1, "name": "John", "revenue": 1000},
            {"id": 2, "name": "Jane", "revenue": 800}
        ]
        
        mock_analysis = {
            "schema": {"id": {"type": "integer"}, "name": {"type": "string"}},
            "quality_summary": {"id": {"completeness": 1.0}, "name": {"completeness": 1.0}}
        }
        
        with patch('src.mcp_server.super_executor') as mock_executor:
            with patch('src.mcp_server.query_processor') as mock_processor:
                mock_executor.execute_query.return_value = mock_sample_data
                mock_processor.analyze_data_structure.return_value = mock_analysis
                
                result = await explore_s3_data(request)
        
        assert result["status"] == "success"
        assert result["s3_path"] == request.s3_path
        assert result["schema"] == mock_analysis["schema"]
        assert result["sample_records"] == mock_sample_data[:10]
        assert result["data_quality"] == mock_analysis["quality_summary"]
        assert result["total_sampled"] == 2
    
    @pytest.mark.asyncio
    async def test_explore_s3_data_failure(self):
        """Test S3 data exploration failure."""
        request = ExploreS3DataRequest(s3_path="s3://invalid-bucket/data/*")
        
        with patch('src.mcp_server.super_executor') as mock_executor:
            mock_executor.execute_query.side_effect = Exception("S3 access failed")
            
            result = await explore_s3_data(request)
        
        assert result["status"] == "error"
        assert "S3 access failed" in result["error"]
        assert result["s3_path"] == request.s3_path
    
    @pytest.mark.asyncio
    async def test_list_s3_files_success(self):
        """Test successful S3 file listing."""
        request = ListS3FilesRequest(bucket="test-bucket", prefix="data/")
        
        mock_files = [
            {
                "key": "data/file1.json",
                "size": 1024,
                "last_modified": "2024-01-01T12:00:00Z",
                "etag": "abc123",
                "storage_class": "STANDARD",
                "s3_url": "s3://test-bucket/data/file1.json"
            },
            {
                "key": "data/file2.json", 
                "size": 2048,
                "last_modified": "2024-01-02T12:00:00Z",
                "etag": "def456",
                "storage_class": "STANDARD",
                "s3_url": "s3://test-bucket/data/file2.json"
            }
        ]
        
        with patch('src.mcp_server.s3_helper') as mock_s3:
            mock_s3.list_files.return_value = mock_files
            
            result = await list_s3_files(request)
        
        assert result["status"] == "success"
        assert result["bucket"] == "test-bucket"
        assert result["prefix"] == "data/"
        assert result["files"] == mock_files
        assert result["total_files"] == 2
    
    @pytest.mark.asyncio
    async def test_list_s3_files_failure(self):
        """Test S3 file listing failure."""
        request = ListS3FilesRequest(bucket="nonexistent-bucket")
        
        with patch('src.mcp_server.s3_helper') as mock_s3:
            mock_s3.list_files.side_effect = Exception("Bucket not found")
            
            result = await list_s3_files(request)
        
        assert result["status"] == "error"
        assert "Bucket not found" in result["error"]
        assert result["bucket"] == "nonexistent-bucket"
    
    def test_lambda_handler_success(self):
        """Test successful Lambda handler execution."""
        mock_event = {"test": "event"}
        mock_context = MagicMock()
        
        with patch('src.mcp_server.validate_super_binary'):
            with patch('src.mcp_server.mcp') as mock_mcp:
                mock_mcp.handle_lambda.return_value = {"statusCode": 200}
                
                result = lambda_handler(mock_event, mock_context)
        
        assert result["statusCode"] == 200
    
    def test_lambda_handler_validation_failure(self):
        """Test Lambda handler with super binary validation failure."""
        mock_event = {"test": "event"}
        mock_context = MagicMock()
        
        with patch('src.mcp_server.validate_super_binary', side_effect=RuntimeError("Binary not found")):
            result = lambda_handler(mock_event, mock_context)
        
        assert result["statusCode"] == 500
        assert "Binary not found" in result["body"]["error"]
    
    def test_lambda_handler_mcp_failure(self):
        """Test Lambda handler with MCP processing failure."""
        mock_event = {"test": "event"}
        mock_context = MagicMock()
        
        with patch('src.mcp_server.validate_super_binary'):
            with patch('src.mcp_server.mcp') as mock_mcp:
                mock_mcp.handle_lambda.side_effect = Exception("MCP processing failed")
                
                result = lambda_handler(mock_event, mock_context)
        
        assert result["statusCode"] == 500
        assert "MCP processing failed" in result["body"]["error"]


class TestRequestModels:
    """Test MCP request model validation."""
    
    def test_query_s3_data_request_valid(self):
        """Test valid QueryS3DataRequest."""
        request = QueryS3DataRequest(
            request="top 10 customers",
            s3_path="s3://bucket/data/*",
            limit=10
        )
        
        assert request.request == "top 10 customers"
        assert request.s3_path == "s3://bucket/data/*"
        assert request.limit == 10
    
    def test_query_s3_data_request_default_limit(self):
        """Test QueryS3DataRequest with default limit."""
        request = QueryS3DataRequest(
            request="count users",
            s3_path="s3://bucket/users/*"
        )
        
        assert request.limit == 100  # Default value
    
    def test_explore_s3_data_request_valid(self):
        """Test valid ExploreS3DataRequest."""
        request = ExploreS3DataRequest(
            s3_path="s3://bucket/data/*",
            sample_size=50
        )
        
        assert request.s3_path == "s3://bucket/data/*"
        assert request.sample_size == 50
    
    def test_explore_s3_data_request_default_sample_size(self):
        """Test ExploreS3DataRequest with default sample size."""
        request = ExploreS3DataRequest(s3_path="s3://bucket/data/*")
        
        assert request.sample_size == 100  # Default value
    
    def test_list_s3_files_request_valid(self):
        """Test valid ListS3FilesRequest."""
        request = ListS3FilesRequest(bucket="test-bucket", prefix="data/")
        
        assert request.bucket == "test-bucket"
        assert request.prefix == "data/"
    
    def test_list_s3_files_request_no_prefix(self):
        """Test ListS3FilesRequest without prefix."""
        request = ListS3FilesRequest(bucket="test-bucket")
        
        assert request.bucket == "test-bucket"
        assert request.prefix is None  # Default value