import pytest
import json
import os
from unittest.mock import patch, MagicMock, AsyncMock
from src.mcp_server import mcp, query_s3_data, explore_s3_data, list_s3_files
from src.query_processor import QueryProcessor
from src.super_executor import SuperExecutor
from src.s3_helper import S3Helper


@pytest.fixture
def integration_setup():
    """Set up integration test environment."""
    with patch.dict('os.environ', {
        'SUPER_BINARY_PATH': '/usr/local/bin/super',
        'AWS_REGION': 'us-east-1',
        'LOG_LEVEL': 'DEBUG'
    }):
        yield


class TestIntegration:
    """Integration tests for end-to-end functionality."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_query_flow(self, integration_setup):
        """Test complete query flow from natural language to results."""
        # Mock data and responses
        mock_super_query = "FROM 's3://test-bucket/sales/*' | SUMMARIZE sum(revenue) BY customer | ORDER BY sum(revenue) DESC | HEAD 5"
        mock_results = [
            {"customer": "ACME Corp", "sum_revenue": 15000.00},
            {"customer": "TechCorp", "sum_revenue": 12000.00},
            {"customer": "DataInc", "sum_revenue": 8500.00}
        ]
        
        # Mock subprocess execution
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = (
            b'{"customer": "ACME Corp", "sum_revenue": 15000.00}\n'
            b'{"customer": "TechCorp", "sum_revenue": 12000.00}\n'
            b'{"customer": "DataInc", "sum_revenue": 8500.00}\n',
            b''
        )
        
        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            with patch('asyncio.wait_for', side_effect=lambda coro, timeout: coro):
                # Test query processor
                processor = QueryProcessor()
                query = await processor.process_query(
                    "top 5 customers by revenue", 
                    "s3://test-bucket/sales/*", 
                    5
                )
                
                # Verify query generation
                assert "customers" in query or "customer" in query
                assert "revenue" in query
                assert "SUMMARIZE" in query
                assert "ORDER BY" in query
                
                # Test super executor
                executor = SuperExecutor()
                results = await executor.execute_query(query, "s3://test-bucket/sales/*")
                
                # Verify results
                assert len(results) == 3
                assert results[0]["customer"] == "ACME Corp"
                assert results[0]["sum_revenue"] == 15000.00
    
    @pytest.mark.asyncio
    async def test_s3_integration_flow(self, integration_setup):
        """Test S3 operations integration."""
        mock_list_response = {
            'Contents': [
                {
                    'Key': 'sales/2024/jan/data.json',
                    'Size': 1024000,
                    'LastModified': '2024-01-15T10:30:00Z',
                    'ETag': '"abc123def456"',
                    'StorageClass': 'STANDARD'
                },
                {
                    'Key': 'sales/2024/feb/data.json',
                    'Size': 2048000,
                    'LastModified': '2024-02-15T10:30:00Z',
                    'ETag': '"def456abc123"'
                }
            ]
        }
        
        mock_head_response = {
            'ContentLength': 1024000,
            'LastModified': '2024-01-15T10:30:00Z',
            'ContentType': 'application/json'
        }
        
        with patch('boto3.client') as mock_boto:
            mock_s3 = MagicMock()
            mock_s3.list_objects_v2.return_value = mock_list_response
            mock_s3.head_object.return_value = mock_head_response
            mock_boto.return_value = mock_s3
            
            # Test S3 helper
            s3_helper = S3Helper()
            
            # Test file listing
            files = await s3_helper.list_files('test-bucket', 'sales/')
            assert len(files) == 2
            assert files[0]['key'] == 'sales/2024/jan/data.json'
            assert files[0]['size'] == 1024000
            
            # Test path validation
            validation = await s3_helper.validate_s3_path('s3://test-bucket/sales/2024/jan/data.json')
            assert validation['valid'] is True
            assert validation['type'] == 'object'
    
    @pytest.mark.asyncio
    async def test_mcp_tool_integration(self, integration_setup):
        """Test MCP tool integration with mocked dependencies."""
        from src.mcp_server import QueryS3DataRequest, ExploreS3DataRequest, ListS3FilesRequest
        
        # Mock all dependencies
        with patch('src.mcp_server.query_processor') as mock_processor:
            with patch('src.mcp_server.super_executor') as mock_executor:
                with patch('src.mcp_server.s3_helper') as mock_s3:
                    
                    # Setup mocks
                    mock_processor.process_query.return_value = "FROM 's3://test/data' | HEAD 10"
                    mock_executor.execute_query.return_value = [{"id": 1, "name": "test"}]
                    mock_processor.analyze_data_structure.return_value = {
                        "schema": {"id": {"type": "integer"}},
                        "quality_summary": {"id": {"completeness": 1.0}}
                    }
                    mock_s3.list_files.return_value = [
                        {"key": "data.json", "size": 1024, "s3_url": "s3://test/data.json"}
                    ]
                    
                    # Test query_s3_data tool
                    query_request = QueryS3DataRequest(
                        request="show me the data",
                        s3_path="s3://test/data"
                    )
                    
                    query_result = await query_s3_data(query_request)
                    assert query_result["status"] == "success"
                    assert len(query_result["results"]) == 1
                    
                    # Test explore_s3_data tool
                    explore_request = ExploreS3DataRequest(s3_path="s3://test/data")
                    
                    explore_result = await explore_s3_data(explore_request)
                    assert explore_result["status"] == "success"
                    assert "schema" in explore_result
                    
                    # Test list_s3_files tool
                    list_request = ListS3FilesRequest(bucket="test")
                    
                    list_result = await list_s3_files(list_request)
                    assert list_result["status"] == "success"
                    assert len(list_result["files"]) == 1
    
    @pytest.mark.asyncio
    async def test_error_handling_integration(self, integration_setup):
        """Test error handling across components."""
        from src.mcp_server import QueryS3DataRequest
        
        # Test query processor error propagation
        with patch('src.mcp_server.query_processor') as mock_processor:
            mock_processor.process_query.side_effect = Exception("Natural language processing failed")
            
            query_request = QueryS3DataRequest(
                request="invalid complex query that fails",
                s3_path="s3://test/data"
            )
            
            result = await query_s3_data(query_request)
            assert result["status"] == "error"
            assert "Natural language processing failed" in result["error"]
        
        # Test super executor error propagation
        with patch('src.mcp_server.query_processor') as mock_processor:
            with patch('src.mcp_server.super_executor') as mock_executor:
                mock_processor.process_query.return_value = "VALID QUERY"
                mock_executor.execute_query.side_effect = RuntimeError("Super binary execution failed")
                
                query_request = QueryS3DataRequest(
                    request="top 10 records",
                    s3_path="s3://test/data"
                )
                
                result = await query_s3_data(query_request)
                assert result["status"] == "error"
                assert "Super binary execution failed" in result["error"]
    
    @pytest.mark.asyncio
    async def test_query_pattern_integration(self, integration_setup):
        """Test various query patterns end-to-end."""
        test_cases = [
            {
                "query": "top 5 products by sales",
                "expected_elements": ["products", "sales", "SUMMARIZE", "ORDER BY", "HEAD 5"]
            },
            {
                "query": "revenue by month",
                "expected_elements": ["revenue", "date_trunc", "month", "SUMMARIZE"]
            },
            {
                "query": "how many users signed up today",
                "expected_elements": ["count", "users", "FROM"]
            },
            {
                "query": "average response time by endpoint",
                "expected_elements": ["avg", "response_time", "endpoint", "SUMMARIZE"]
            }
        ]
        
        processor = QueryProcessor()
        
        for case in test_cases:
            query_result = await processor.process_query(
                case["query"], 
                "s3://test/data/*", 
                100
            )
            
            # Verify expected elements are present
            for element in case["expected_elements"]:
                assert element.lower() in query_result.lower(), \
                    f"Expected '{element}' in query result for '{case['query']}'"
    
    def test_environment_configuration(self, integration_setup):
        """Test environment variable configuration."""
        # Test default values
        executor = SuperExecutor()
        assert executor.super_binary_path == '/usr/local/bin/super'
        assert executor.query_timeout == 300
        assert executor.max_results == 10000
        
        # Test custom values
        with patch.dict('os.environ', {
            'SUPER_BINARY_PATH': '/custom/path/super',
            'QUERY_TIMEOUT': '600',
            'MAX_RESULTS': '5000'
        }):
            custom_executor = SuperExecutor()
            assert custom_executor.super_binary_path == '/custom/path/super'
            assert custom_executor.query_timeout == 600
            assert custom_executor.max_results == 5000
    
    @pytest.mark.asyncio
    async def test_data_format_handling(self, integration_setup):
        """Test handling of different data formats."""
        # Test JSON data
        json_output = '{"id": 1, "name": "test", "value": 100.5}\n{"id": 2, "name": "test2", "value": 200.0}\n'
        
        executor = SuperExecutor()
        results = executor._parse_super_output(json_output)
        
        assert len(results) == 2
        assert results[0]["id"] == 1
        assert results[0]["value"] == 100.5
        assert results[1]["name"] == "test2"
        
        # Test empty output
        empty_results = executor._parse_super_output('')
        assert empty_results == []
        
        # Test malformed JSON handling
        malformed_output = '{"id": 1, "name": "test"}\n{invalid json}\n{"id": 2, "name": "test2"}\n'
        filtered_results = executor._parse_super_output(malformed_output)
        assert len(filtered_results) == 2  # Should skip malformed line
        assert filtered_results[0]["id"] == 1
        assert filtered_results[1]["id"] == 2
    
    def test_component_initialization(self, integration_setup):
        """Test proper component initialization."""
        # Test query processor initialization
        processor = QueryProcessor()
        assert hasattr(processor, 'query_patterns')
        assert 'top_n' in processor.query_patterns
        assert 'time_series' in processor.query_patterns
        assert 'counting' in processor.query_patterns
        
        # Test super executor initialization
        executor = SuperExecutor()
        assert hasattr(executor, 'super_binary_path')
        assert hasattr(executor, 'query_timeout')
        assert hasattr(executor, 'max_results')
        
        # Test S3 helper initialization (with mocked boto3)
        with patch('boto3.client'):
            s3_helper = S3Helper()
            assert hasattr(s3_helper, 's3_client')
    
    @pytest.mark.asyncio
    async def test_result_formatting_integration(self, integration_setup):
        """Test result formatting across components."""
        mock_results = [
            {"product": "Laptop", "revenue": 15000, "count": 25},
            {"product": "Phone", "revenue": 12000, "count": 40},
            {"product": "Tablet", "revenue": 8000, "count": 15}
        ]
        
        executor = SuperExecutor()
        
        # Test display formatting
        formatted = executor.format_results_for_display(mock_results)
        assert "product" in formatted
        assert "revenue" in formatted
        assert "Laptop" in formatted
        assert "|" in formatted  # Table format indicator
        
        # Test statistics generation
        stats = executor.get_query_statistics(mock_results)
        assert stats["total_records"] == 3
        assert "product" in stats["fields"]
        assert "revenue" in stats["fields"]
        assert stats["field_count"] == 3