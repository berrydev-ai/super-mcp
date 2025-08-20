import os
import json
import asyncio
import logging
from typing import Any, Dict, List, Optional
from subprocess import PIPE, TimeoutExpired

logger = logging.getLogger(__name__)


class SuperExecutor:
    """Executes super binary commands server-side for S3 data analytics."""
    
    def __init__(self):
        self.super_binary_path = os.environ.get('SUPER_BINARY_PATH', '/usr/local/bin/super')
        self.query_timeout = int(os.environ.get('QUERY_TIMEOUT', '300'))  # 5 minutes
        self.max_results = int(os.environ.get('MAX_RESULTS', '10000'))
        
        # Validate binary exists
        if not os.path.exists(self.super_binary_path):
            logger.warning(f"Super binary not found at {self.super_binary_path}")
    
    async def execute_query(self, query: str, s3_path: str) -> List[Dict[str, Any]]:
        """Execute a SuperSQL query against S3 data.
        
        Args:
            query: SuperSQL query string
            s3_path: S3 path to query
            
        Returns:
            List of result records as dictionaries
            
        Raises:
            RuntimeError: If super binary execution fails
        """
        try:
            logger.info(f"Executing super query: {query}")
            logger.info(f"Against S3 path: {s3_path}")
            
            # Prepare the super command
            cmd = [
                self.super_binary_path,
                '-f', 'json',  # Output format: JSON
                '-c', query,   # Query string
                s3_path       # Data source
            ]
            
            # Execute the command asynchronously
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=PIPE,
                stderr=PIPE,
                env=self._get_process_env()
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.query_timeout
                )
                
                if process.returncode != 0:
                    error_msg = stderr.decode('utf-8') if stderr else "Unknown error"
                    raise RuntimeError(f"Super query failed: {error_msg}")
                
                # Parse JSON output
                output = stdout.decode('utf-8').strip()
                if not output:
                    return []
                
                return self._parse_super_output(output)
                
            except TimeoutExpired:
                process.kill()
                await process.wait()
                raise RuntimeError(f"Query timeout after {self.query_timeout} seconds")
                
        except FileNotFoundError:
            raise RuntimeError(f"Super binary not found at {self.super_binary_path}")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse super output as JSON: {str(e)}")
        except Exception as e:
            logger.error(f"Super execution error: {str(e)}")
            raise RuntimeError(f"Super execution failed: {str(e)}")
    
    def _parse_super_output(self, output: str) -> List[Dict[str, Any]]:
        """Parse super binary JSON output into structured data.
        
        Args:
            output: Raw JSON output from super
            
        Returns:
            List of parsed records
        """
        results = []
        
        # Super outputs JSONL format (one JSON object per line)
        for line in output.strip().split('\n'):
            if line.strip():
                try:
                    record = json.loads(line)
                    results.append(record)
                    
                    # Limit results to prevent memory issues
                    if len(results) >= self.max_results:
                        logger.warning(f"Result set truncated to {self.max_results} records")
                        break
                        
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse line as JSON: {line[:100]}...")
                    continue
        
        return results
    
    def _get_process_env(self) -> Dict[str, str]:
        """Get environment variables for super process execution.
        
        Returns:
            Environment dictionary with AWS credentials and other settings
        """
        env = os.environ.copy()
        
        # Ensure AWS credentials are available
        aws_vars = ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_SESSION_TOKEN', 'AWS_REGION']
        for var in aws_vars:
            if var in os.environ:
                env[var] = os.environ[var]
        
        # Set default AWS region if not specified
        if 'AWS_REGION' not in env:
            env['AWS_REGION'] = 'us-east-1'
        
        return env
    
    async def test_super_binary(self) -> Dict[str, Any]:
        """Test that super binary is working and accessible.
        
        Returns:
            Status information about super binary
        """
        try:
            # Test with --version flag
            process = await asyncio.create_subprocess_exec(
                self.super_binary_path,
                '--version',
                stdout=PIPE,
                stderr=PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=10
            )
            
            if process.returncode == 0:
                version = stdout.decode('utf-8').strip()
                return {
                    "status": "success",
                    "binary_path": self.super_binary_path,
                    "version": version,
                    "accessible": True
                }
            else:
                error = stderr.decode('utf-8') if stderr else "Unknown error"
                return {
                    "status": "error",
                    "binary_path": self.super_binary_path,
                    "error": error,
                    "accessible": False
                }
                
        except FileNotFoundError:
            return {
                "status": "error",
                "binary_path": self.super_binary_path,
                "error": "Super binary not found",
                "accessible": False
            }
        except Exception as e:
            return {
                "status": "error",
                "binary_path": self.super_binary_path,
                "error": str(e),
                "accessible": False
            }
    
    async def validate_s3_access(self, s3_path: str) -> Dict[str, Any]:
        """Validate that super can access the specified S3 path.
        
        Args:
            s3_path: S3 path to validate
            
        Returns:
            Validation status and information
        """
        try:
            # Try to execute a simple HEAD query to test access
            test_query = "HEAD 1"
            
            process = await asyncio.create_subprocess_exec(
                self.super_binary_path,
                '-f', 'json',
                '-c', test_query,
                s3_path,
                stdout=PIPE,
                stderr=PIPE,
                env=self._get_process_env()
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=30
            )
            
            if process.returncode == 0:
                return {
                    "status": "success",
                    "s3_path": s3_path,
                    "accessible": True,
                    "message": "S3 path is accessible"
                }
            else:
                error = stderr.decode('utf-8') if stderr else "Unknown error"
                return {
                    "status": "error",
                    "s3_path": s3_path,
                    "accessible": False,
                    "error": error
                }
                
        except Exception as e:
            return {
                "status": "error",
                "s3_path": s3_path,
                "accessible": False,
                "error": str(e)
            }
    
    def format_results_for_display(self, results: List[Dict[str, Any]]) -> str:
        """Format query results for human-readable display.
        
        Args:
            results: List of result records
            
        Returns:
            Formatted string representation
        """
        if not results:
            return "No results found."
        
        # Create a simple table format
        if isinstance(results[0], dict):
            headers = list(results[0].keys())
            
            # Format as table
            output = []
            
            # Header row
            header_row = " | ".join(f"{h:15}" for h in headers)
            separator = "-" * len(header_row)
            
            output.append(header_row)
            output.append(separator)
            
            # Data rows
            for record in results[:20]:  # Limit display to first 20 rows
                row_values = []
                for header in headers:
                    value = str(record.get(header, ""))
                    # Truncate long values
                    if len(value) > 15:
                        value = value[:12] + "..."
                    row_values.append(f"{value:15}")
                
                output.append(" | ".join(row_values))
            
            if len(results) > 20:
                output.append(f"... and {len(results) - 20} more rows")
            
            return "\n".join(output)
        
        else:
            # Handle non-dictionary results
            return "\n".join(str(result) for result in results[:20])
    
    def get_query_statistics(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get statistics about query results.
        
        Args:
            results: Query results
            
        Returns:
            Statistics dictionary
        """
        if not results:
            return {"total_records": 0, "fields": []}
        
        stats = {
            "total_records": len(results),
            "truncated": len(results) >= self.max_results,
            "fields": []
        }
        
        if isinstance(results[0], dict):
            stats["fields"] = list(results[0].keys())
            stats["field_count"] = len(stats["fields"])
        
        return stats