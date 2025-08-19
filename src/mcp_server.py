#!/usr/bin/env python3

import os
import logging
from typing import Any, Dict, List, Optional

from fastmcp import FastMCP
from pydantic import BaseModel

from .query_processor import QueryProcessor
from .super_executor import SuperExecutor
from .s3_helper import S3Helper

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize MCP server
mcp = FastMCP("S3 Super MCP Server")

# Initialize components
query_processor = QueryProcessor()
super_executor = SuperExecutor()
s3_helper = S3Helper()


def validate_super_binary():
    """Validate that super binary is available and executable."""
    super_path = os.environ.get('SUPER_BINARY_PATH', '/usr/local/bin/super')
    
    if not os.path.exists(super_path):
        raise RuntimeError(f"Super binary not found at {super_path}")
    
    if not os.access(super_path, os.X_OK):
        raise RuntimeError(f"Super binary not executable at {super_path}")
    
    logger.info(f"Super binary validated at {super_path}")


class QueryS3DataRequest(BaseModel):
    request: str
    s3_path: str
    limit: int = 100


class ExploreS3DataRequest(BaseModel):
    s3_path: str
    sample_size: int = 100


class ListS3FilesRequest(BaseModel):
    bucket: str
    prefix: Optional[str] = None


@mcp.tool()
async def query_s3_data(request: QueryS3DataRequest) -> Dict[str, Any]:
    """Execute natural language queries against S3 data using super library.
    
    Args:
        request: Natural language business question
        s3_path: S3 URL (s3://bucket/path/*)
        limit: Maximum number of results to return
    
    Returns:
        Formatted table or structured data with query results
    """
    try:
        logger.info(f"Processing query: {request.request} on {request.s3_path}")
        
        # Convert natural language to SuperSQL
        super_query = await query_processor.process_query(
            request.request, 
            request.s3_path, 
            request.limit
        )
        
        # Execute super binary command
        results = await super_executor.execute_query(super_query, request.s3_path)
        
        return {
            "status": "success",
            "query": super_query,
            "results": results,
            "record_count": len(results) if isinstance(results, list) else None
        }
        
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "query": request.request
        }


@mcp.tool()
async def explore_s3_data(request: ExploreS3DataRequest) -> Dict[str, Any]:
    """Discover data structure and schema for query building.
    
    Args:
        s3_path: S3 URL to analyze
        sample_size: Number of records to sample for analysis
    
    Returns:
        Field names, data types, sample records, and data quality summary
    """
    try:
        logger.info(f"Exploring data structure at {request.s3_path}")
        
        # Use super to analyze data structure
        schema_query = f"FROM '{request.s3_path}' | HEAD {request.sample_size}"
        sample_data = await super_executor.execute_query(schema_query, request.s3_path)
        
        # Analyze the sample data
        analysis = await query_processor.analyze_data_structure(sample_data)
        
        return {
            "status": "success",
            "s3_path": request.s3_path,
            "schema": analysis["schema"],
            "sample_records": sample_data[:10] if isinstance(sample_data, list) else sample_data,
            "data_quality": analysis["quality_summary"],
            "total_sampled": len(sample_data) if isinstance(sample_data, list) else 1
        }
        
    except Exception as e:
        logger.error(f"Error exploring data: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "s3_path": request.s3_path
        }


@mcp.tool()
async def list_s3_files(request: ListS3FilesRequest) -> Dict[str, Any]:
    """Browse available data sources in S3.
    
    Args:
        bucket: S3 bucket name
        prefix: Optional path prefix filter
    
    Returns:
        List of S3 objects with sizes and modification dates
    """
    try:
        logger.info(f"Listing S3 files in bucket: {request.bucket}, prefix: {request.prefix}")
        
        # Use S3 helper to list files
        files = await s3_helper.list_files(request.bucket, request.prefix)
        
        return {
            "status": "success",
            "bucket": request.bucket,
            "prefix": request.prefix,
            "files": files,
            "total_files": len(files)
        }
        
    except Exception as e:
        logger.error(f"Error listing S3 files: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "bucket": request.bucket,
            "prefix": request.prefix
        }


def lambda_handler(event, context):
    """AWS Lambda handler for serverless deployment."""
    try:
        # Validate super binary on Lambda startup
        validate_super_binary()
        
        # Process the MCP request
        return mcp.handle_lambda(event, context)
        
    except Exception as e:
        logger.error(f"Lambda handler error: {str(e)}")
        return {
            "statusCode": 500,
            "body": {"error": str(e)}
        }


def main():
    """Main entry point for local development."""
    try:
        # Validate super binary
        validate_super_binary()
        
        # Run the MCP server
        mcp.run()
        
    except Exception as e:
        logger.error(f"Server startup error: {str(e)}")
        raise


if __name__ == "__main__":
    main()