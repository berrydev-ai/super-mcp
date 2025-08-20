import boto3
import logging
from typing import Dict, List, Optional, Any
from botocore.exceptions import ClientError, NoCredentialsError
from datetime import datetime

logger = logging.getLogger(__name__)


class S3Helper:
    """Helper class for S3 operations and path validation."""
    
    def __init__(self):
        self.s3_client = None
        self._initialize_s3_client()
    
    def _initialize_s3_client(self):
        """Initialize S3 client with error handling."""
        try:
            self.s3_client = boto3.client('s3')
            logger.info("S3 client initialized successfully")
        except NoCredentialsError:
            logger.error("AWS credentials not found")
            self.s3_client = None
        except Exception as e:
            logger.error(f"Failed to initialize S3 client: {str(e)}")
            self.s3_client = None
    
    async def list_files(self, bucket: str, prefix: Optional[str] = None, max_keys: int = 1000) -> List[Dict[str, Any]]:
        """List files in an S3 bucket with optional prefix filter.
        
        Args:
            bucket: S3 bucket name
            prefix: Optional prefix to filter objects
            max_keys: Maximum number of objects to return
            
        Returns:
            List of file information dictionaries
            
        Raises:
            RuntimeError: If S3 operation fails
        """
        if not self.s3_client:
            raise RuntimeError("S3 client not initialized. Check AWS credentials.")
        
        try:
            logger.info(f"Listing files in bucket: {bucket}, prefix: {prefix}")
            
            # Prepare request parameters
            params = {
                'Bucket': bucket,
                'MaxKeys': max_keys
            }
            
            if prefix:
                params['Prefix'] = prefix
            
            # List objects
            response = self.s3_client.list_objects_v2(**params)
            
            files = []
            
            if 'Contents' in response:
                for obj in response['Contents']:
                    file_info = {
                        'key': obj['Key'],
                        'size': obj['Size'],
                        'last_modified': obj['LastModified'].isoformat(),
                        'etag': obj['ETag'].strip('"'),
                        'storage_class': obj.get('StorageClass', 'STANDARD'),
                        's3_url': f"s3://{bucket}/{obj['Key']}"
                    }
                    files.append(file_info)
            
            # Handle pagination if there are more results
            while response.get('IsTruncated', False) and len(files) < max_keys:
                params['ContinuationToken'] = response['NextContinuationToken']
                response = self.s3_client.list_objects_v2(**params)
                
                if 'Contents' in response:
                    for obj in response['Contents']:
                        if len(files) >= max_keys:
                            break
                            
                        file_info = {
                            'key': obj['Key'],
                            'size': obj['Size'],
                            'last_modified': obj['LastModified'].isoformat(),
                            'etag': obj['ETag'].strip('"'),
                            'storage_class': obj.get('StorageClass', 'STANDARD'),
                            's3_url': f"s3://{bucket}/{obj['Key']}"
                        }
                        files.append(file_info)
            
            logger.info(f"Found {len(files)} files in bucket {bucket}")
            return files
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_msg = e.response['Error']['Message']
            
            if error_code == 'NoSuchBucket':
                raise RuntimeError(f"S3 bucket '{bucket}' does not exist")
            elif error_code == 'AccessDenied':
                raise RuntimeError(f"Access denied to S3 bucket '{bucket}'")
            else:
                raise RuntimeError(f"S3 error ({error_code}): {error_msg}")
                
        except Exception as e:
            logger.error(f"Error listing S3 files: {str(e)}")
            raise RuntimeError(f"Failed to list S3 files: {str(e)}")
    
    async def validate_s3_path(self, s3_path: str) -> Dict[str, Any]:
        """Validate that an S3 path exists and is accessible.
        
        Args:
            s3_path: S3 URL (s3://bucket/path)
            
        Returns:
            Validation result dictionary
        """
        if not self.s3_client:
            return {
                "valid": False,
                "error": "S3 client not initialized. Check AWS credentials."
            }
        
        try:
            # Parse S3 path
            bucket, key = self._parse_s3_path(s3_path)
            
            if not bucket:
                return {
                    "valid": False,
                    "error": f"Invalid S3 path format: {s3_path}"
                }
            
            # Check if it's a wildcard path
            if '*' in key or key.endswith('/'):
                # For wildcard paths, try to list objects
                prefix = key.rstrip('*')
                response = self.s3_client.list_objects_v2(
                    Bucket=bucket,
                    Prefix=prefix,
                    MaxKeys=1
                )
                
                if 'Contents' in response and len(response['Contents']) > 0:
                    return {
                        "valid": True,
                        "type": "prefix",
                        "bucket": bucket,
                        "prefix": prefix,
                        "sample_objects": [obj['Key'] for obj in response['Contents'][:5]]
                    }
                else:
                    return {
                        "valid": False,
                        "error": f"No objects found with prefix: {prefix}"
                    }
            else:
                # For specific object paths, check if object exists
                try:
                    response = self.s3_client.head_object(Bucket=bucket, Key=key)
                    return {
                        "valid": True,
                        "type": "object",
                        "bucket": bucket,
                        "key": key,
                        "size": response.get('ContentLength', 0),
                        "last_modified": response.get('LastModified', '').isoformat() if response.get('LastModified') else None,
                        "content_type": response.get('ContentType', 'unknown')
                    }
                except ClientError as e:
                    if e.response['Error']['Code'] == '404':
                        return {
                            "valid": False,
                            "error": f"Object not found: {s3_path}"
                        }
                    else:
                        raise e
                        
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_msg = e.response['Error']['Message']
            
            return {
                "valid": False,
                "error": f"S3 error ({error_code}): {error_msg}"
            }
            
        except Exception as e:
            logger.error(f"Error validating S3 path: {str(e)}")
            return {
                "valid": False,
                "error": f"Validation error: {str(e)}"
            }
    
    def _parse_s3_path(self, s3_path: str) -> tuple:
        """Parse S3 URL into bucket and key components.
        
        Args:
            s3_path: S3 URL (s3://bucket/path)
            
        Returns:
            Tuple of (bucket, key)
        """
        if not s3_path.startswith('s3://'):
            return None, None
        
        # Remove s3:// prefix
        path = s3_path[5:]
        
        # Split into bucket and key
        parts = path.split('/', 1)
        bucket = parts[0]
        key = parts[1] if len(parts) > 1 else ''
        
        return bucket, key
    
    async def get_bucket_info(self, bucket: str) -> Dict[str, Any]:
        """Get information about an S3 bucket.
        
        Args:
            bucket: S3 bucket name
            
        Returns:
            Bucket information dictionary
        """
        if not self.s3_client:
            raise RuntimeError("S3 client not initialized. Check AWS credentials.")
        
        try:
            # Check if bucket exists and get basic info
            response = self.s3_client.head_bucket(Bucket=bucket)
            
            # Get bucket location
            try:
                location_response = self.s3_client.get_bucket_location(Bucket=bucket)
                region = location_response.get('LocationConstraint') or 'us-east-1'
            except Exception:
                region = 'unknown'
            
            # Get approximate object count (limited sample)
            try:
                objects_response = self.s3_client.list_objects_v2(
                    Bucket=bucket,
                    MaxKeys=1000
                )
                
                object_count = len(objects_response.get('Contents', []))
                is_truncated = objects_response.get('IsTruncated', False)
                
                if is_truncated:
                    object_count_desc = f"{object_count}+ objects"
                else:
                    object_count_desc = f"{object_count} objects"
                    
            except Exception:
                object_count_desc = "unknown"
            
            return {
                "bucket": bucket,
                "exists": True,
                "region": region,
                "object_count": object_count_desc,
                "accessible": True
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            
            if error_code == 'NoSuchBucket':
                return {
                    "bucket": bucket,
                    "exists": False,
                    "error": "Bucket does not exist"
                }
            elif error_code in ['AccessDenied', '403']:
                return {
                    "bucket": bucket,
                    "exists": True,
                    "accessible": False,
                    "error": "Access denied"
                }
            else:
                return {
                    "bucket": bucket,
                    "exists": False,
                    "error": f"Error ({error_code}): {e.response['Error']['Message']}"
                }
                
        except Exception as e:
            return {
                "bucket": bucket,
                "exists": False,
                "error": f"Unknown error: {str(e)}"
            }
    
    def format_file_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format.
        
        Args:
            size_bytes: Size in bytes
            
        Returns:
            Formatted size string
        """
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        size = float(size_bytes)
        
        while size >= 1024.0 and i < len(size_names) - 1:
            size /= 1024.0
            i += 1
        
        return f"{size:.1f} {size_names[i]}"
    
    def get_s3_credentials_status(self) -> Dict[str, Any]:
        """Check the status of AWS credentials.
        
        Returns:
            Credentials status information
        """
        try:
            if not self.s3_client:
                return {
                    "configured": False,
                    "error": "S3 client not initialized"
                }
            
            # Try to get caller identity to test credentials
            sts_client = boto3.client('sts')
            identity = sts_client.get_caller_identity()
            
            return {
                "configured": True,
                "account_id": identity.get('Account', 'unknown'),
                "user_arn": identity.get('Arn', 'unknown')
            }
            
        except NoCredentialsError:
            return {
                "configured": False,
                "error": "AWS credentials not found"
            }
        except ClientError as e:
            return {
                "configured": False,
                "error": f"AWS credentials invalid: {e.response['Error']['Message']}"
            }
        except Exception as e:
            return {
                "configured": False,
                "error": f"Unknown error: {str(e)}"
            }