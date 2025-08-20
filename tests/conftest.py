import pytest
import asyncio
import os
from unittest.mock import patch


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_environment():
    """Mock environment variables for testing."""
    env_vars = {
        'SUPER_BINARY_PATH': '/usr/local/bin/super',
        'AWS_REGION': 'us-east-1',
        'LOG_LEVEL': 'DEBUG',
        'QUERY_TIMEOUT': '300',
        'MAX_RESULTS': '10000'
    }
    
    with patch.dict('os.environ', env_vars):
        yield env_vars


@pytest.fixture
def sample_s3_data():
    """Sample S3 data for testing."""
    return [
        {
            "id": 1,
            "customer": "ACME Corp",
            "product": "Widget A",
            "revenue": 1500.00,
            "quantity": 10,
            "date": "2024-01-15",
            "timestamp": "2024-01-15T10:30:00Z",
            "region": "US-East"
        },
        {
            "id": 2, 
            "customer": "TechCorp",
            "product": "Widget B",
            "revenue": 2200.00,
            "quantity": 15,
            "date": "2024-01-16",
            "timestamp": "2024-01-16T14:20:00Z",
            "region": "US-West"
        },
        {
            "id": 3,
            "customer": "DataInc",
            "product": "Widget A", 
            "revenue": 1800.00,
            "quantity": 12,
            "date": "2024-01-17",
            "timestamp": "2024-01-17T09:15:00Z",
            "region": "EU"
        }
    ]


@pytest.fixture
def sample_log_data():
    """Sample log data for testing."""
    return [
        {
            "timestamp": "2024-01-15T10:30:00Z",
            "level": "INFO",
            "service": "api-gateway",
            "endpoint": "/users",
            "method": "GET",
            "response_time": 120,
            "status_code": 200
        },
        {
            "timestamp": "2024-01-15T10:31:00Z",
            "level": "ERROR",
            "service": "user-service",
            "endpoint": "/users/123",
            "method": "POST",
            "response_time": 5000,
            "status_code": 500,
            "error": "Database connection failed"
        },
        {
            "timestamp": "2024-01-15T10:32:00Z",
            "level": "INFO",
            "service": "api-gateway",
            "endpoint": "/products",
            "method": "GET", 
            "response_time": 85,
            "status_code": 200
        }
    ]


@pytest.fixture
def mock_s3_files():
    """Mock S3 file listing response."""
    return [
        {
            "key": "sales/2024/january/transactions.json",
            "size": 1024000,
            "last_modified": "2024-01-31T23:59:59Z",
            "etag": "abc123def456",
            "storage_class": "STANDARD",
            "s3_url": "s3://test-bucket/sales/2024/january/transactions.json"
        },
        {
            "key": "sales/2024/february/transactions.json", 
            "size": 2048000,
            "last_modified": "2024-02-29T23:59:59Z",
            "etag": "def456abc123",
            "storage_class": "STANDARD",
            "s3_url": "s3://test-bucket/sales/2024/february/transactions.json"
        },
        {
            "key": "logs/2024/january/app.jsonl",
            "size": 512000,
            "last_modified": "2024-01-31T23:59:59Z", 
            "etag": "xyz789abc123",
            "storage_class": "GLACIER",
            "s3_url": "s3://test-bucket/logs/2024/january/app.jsonl"
        }
    ]


@pytest.fixture  
def query_test_cases():
    """Test cases for query processing."""
    return [
        {
            "description": "Top N query",
            "input": "top 5 customers by revenue",
            "s3_path": "s3://bucket/sales/*",
            "expected_patterns": ["customers", "revenue", "SUMMARIZE", "ORDER BY", "DESC", "HEAD 5"]
        },
        {
            "description": "Time series query",
            "input": "sales by month",
            "s3_path": "s3://bucket/sales/*", 
            "expected_patterns": ["sales", "date_trunc", "month", "SUMMARIZE"]
        },
        {
            "description": "Counting query",
            "input": "how many orders today",
            "s3_path": "s3://bucket/orders/*",
            "expected_patterns": ["count", "orders", "FROM"]
        },
        {
            "description": "Aggregation query",
            "input": "average order value by region",
            "s3_path": "s3://bucket/orders/*",
            "expected_patterns": ["avg", "order_value", "region", "SUMMARIZE"]
        },
        {
            "description": "Filtering query", 
            "input": "errors from payment service",
            "s3_path": "s3://bucket/logs/*",
            "expected_patterns": ["errors", "payment", "FROM"]
        }
    ]


# Async test helpers
@pytest.fixture
def async_mock():
    """Helper for creating async mocks."""
    def _async_mock(*args, **kwargs):
        from unittest.mock import AsyncMock
        return AsyncMock(*args, **kwargs)
    return _async_mock


# Performance test helpers
@pytest.fixture
def large_dataset():
    """Generate a large dataset for performance testing."""
    import random
    from datetime import datetime, timedelta
    
    base_date = datetime(2024, 1, 1)
    customers = ["ACME Corp", "TechCorp", "DataInc", "CloudCo", "AIStart"]
    products = ["Widget A", "Widget B", "Service X", "Service Y", "Premium Plan"]
    regions = ["US-East", "US-West", "EU", "ASIA", "LATAM"]
    
    dataset = []
    for i in range(1000):
        dataset.append({
            "id": i + 1,
            "customer": random.choice(customers),
            "product": random.choice(products),
            "revenue": round(random.uniform(100, 5000), 2),
            "quantity": random.randint(1, 50),
            "date": (base_date + timedelta(days=random.randint(0, 365))).strftime("%Y-%m-%d"),
            "timestamp": (base_date + timedelta(
                days=random.randint(0, 365), 
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59)
            )).isoformat() + "Z",
            "region": random.choice(regions)
        })
    
    return dataset


# Error simulation helpers
@pytest.fixture 
def error_scenarios():
    """Common error scenarios for testing."""
    return {
        "s3_access_denied": {
            "error_code": "AccessDenied",
            "error_message": "Access Denied to S3 bucket",
            "http_status": 403
        },
        "s3_no_such_bucket": {
            "error_code": "NoSuchBucket", 
            "error_message": "The specified bucket does not exist",
            "http_status": 404
        },
        "super_binary_not_found": {
            "error_type": "FileNotFoundError",
            "error_message": "Super binary not found at specified path"
        },
        "super_query_timeout": {
            "error_type": "TimeoutError",
            "error_message": "Query execution timeout after 300 seconds"
        },
        "super_invalid_query": {
            "error_code": 1,
            "stderr": "Error: Invalid SuperSQL syntax"
        }
    }