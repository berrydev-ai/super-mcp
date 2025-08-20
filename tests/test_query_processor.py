import pytest
from src.query_processor import QueryProcessor


@pytest.fixture
def query_processor():
    return QueryProcessor()


class TestQueryProcessor:
    """Test natural language to SuperSQL query processing."""
    
    @pytest.mark.asyncio
    async def test_top_n_query(self, query_processor):
        """Test top N analysis queries."""
        query = "top 10 customers by revenue"
        s3_path = "s3://test-bucket/sales/*"
        
        result = await query_processor.process_query(query, s3_path)
        
        assert "customers" in result
        assert "revenue" in result
        assert "SUMMARIZE" in result
        assert "ORDER BY" in result
        assert "DESC" in result
        assert "HEAD 10" in result
    
    @pytest.mark.asyncio
    async def test_time_series_query(self, query_processor):
        """Test time series analysis queries."""
        query = "revenue by month"
        s3_path = "s3://test-bucket/sales/*"
        
        result = await query_processor.process_query(query, s3_path)
        
        assert "revenue" in result
        assert "date_trunc" in result
        assert "month" in result
        assert "SUMMARIZE" in result
    
    @pytest.mark.asyncio
    async def test_counting_query(self, query_processor):
        """Test counting queries."""
        query = "how many users signed up today"
        s3_path = "s3://test-bucket/users/*"
        
        result = await query_processor.process_query(query, s3_path)
        
        assert "count" in result
        assert "FROM" in result
        assert s3_path in result
    
    @pytest.mark.asyncio
    async def test_aggregation_query(self, query_processor):
        """Test aggregation queries."""
        query = "average response time by endpoint"
        s3_path = "s3://test-bucket/logs/*"
        
        result = await query_processor.process_query(query, s3_path)
        
        assert "avg" in result
        assert "response_time" in result
        assert "endpoint" in result
        assert "SUMMARIZE" in result
    
    @pytest.mark.asyncio
    async def test_filtering_query(self, query_processor):
        """Test filtering queries."""
        query = "errors from API service"
        s3_path = "s3://test-bucket/logs/*"
        
        result = await query_processor.process_query(query, s3_path)
        
        assert "FROM" in result
        assert s3_path in result
    
    def test_clean_field_name(self, query_processor):
        """Test field name cleaning."""
        assert query_processor._clean_field_name("the customer name") == "customer_name"
        assert query_processor._clean_field_name("response time") == "response_time"
        assert query_processor._clean_field_name("API calls") == "api_calls"
    
    def test_infer_metric_function(self, query_processor):
        """Test metric function inference."""
        assert query_processor._infer_metric_function("revenue") == "sum"
        assert query_processor._infer_metric_function("count") == "count"
        assert query_processor._infer_metric_function("average_time") == "avg"
        assert query_processor._infer_metric_function("max_value") == "max"
        assert query_processor._infer_metric_function("min_price") == "min"
    
    @pytest.mark.asyncio
    async def test_analyze_data_structure(self, query_processor):
        """Test data structure analysis."""
        sample_data = [
            {"id": 1, "name": "John", "revenue": 1000.50, "date": "2024-01-01"},
            {"id": 2, "name": "Jane", "revenue": 2000.75, "date": "2024-01-02"},
            {"id": 3, "name": None, "revenue": 1500.00, "date": "2024-01-03"}
        ]
        
        result = await query_processor.analyze_data_structure(sample_data)
        
        assert "schema" in result
        assert "quality_summary" in result
        assert "id" in result["schema"]
        assert "name" in result["schema"]
        assert "revenue" in result["schema"]
        assert result["schema"]["id"]["type"] == "integer"
        assert result["schema"]["revenue"]["type"] == "float"
        assert result["quality_summary"]["name"]["completeness"] < 1.0  # Has nulls
    
    def test_data_type_inference(self, query_processor):
        """Test data type inference."""
        assert query_processor._infer_data_type(123) == "integer"
        assert query_processor._infer_data_type(123.45) == "float"
        assert query_processor._infer_data_type("hello") == "string"
        assert query_processor._infer_data_type(True) == "boolean"
        assert query_processor._infer_data_type(None) == "null"
        assert query_processor._infer_data_type([1, 2, 3]) == "array"
        assert query_processor._infer_data_type({"key": "value"}) == "object"
    
    def test_timestamp_detection(self, query_processor):
        """Test timestamp pattern detection."""
        assert query_processor._looks_like_timestamp("2024-01-01T12:00:00")
        assert query_processor._looks_like_timestamp("2024-01-01 12:00:00")
        assert not query_processor._looks_like_timestamp("not a timestamp")
    
    def test_date_detection(self, query_processor):
        """Test date pattern detection."""
        assert query_processor._looks_like_date("2024-01-01")
        assert query_processor._looks_like_date("01/01/2024")
        assert not query_processor._looks_like_date("not a date")