import pytest
from unittest.mock import patch, MagicMock
from botocore.exceptions import ClientError, NoCredentialsError
from datetime import datetime
from src.s3_helper import S3Helper


@pytest.fixture
def s3_helper():
    with patch('boto3.client'):
        return S3Helper()


class TestS3Helper:
    """Test S3 operations and utilities."""
    
    @pytest.mark.asyncio
    async def test_list_files_success(self, s3_helper):
        """Test successful file listing."""
        mock_response = {
            'Contents': [
                {
                    'Key': 'data/file1.json',
                    'Size': 1024,
                    'LastModified': datetime(2024, 1, 1, 12, 0, 0),
                    'ETag': '"abc123"',
                    'StorageClass': 'STANDARD'
                },
                {
                    'Key': 'data/file2.json',
                    'Size': 2048,
                    'LastModified': datetime(2024, 1, 2, 12, 0, 0),
                    'ETag': '"def456"'
                }
            ]
        }
        
        s3_helper.s3_client = MagicMock()
        s3_helper.s3_client.list_objects_v2.return_value = mock_response
        
        result = await s3_helper.list_files('test-bucket', 'data/')
        
        assert len(result) == 2
        assert result[0]['key'] == 'data/file1.json'
        assert result[0]['size'] == 1024
        assert result[0]['storage_class'] == 'STANDARD'
        assert result[0]['s3_url'] == 's3://test-bucket/data/file1.json'
        assert result[1]['key'] == 'data/file2.json'
        assert 'StorageClass' not in mock_response['Contents'][1]  # Test default
    
    @pytest.mark.asyncio
    async def test_list_files_no_contents(self, s3_helper):
        """Test file listing with no contents."""
        mock_response = {}
        
        s3_helper.s3_client = MagicMock()
        s3_helper.s3_client.list_objects_v2.return_value = mock_response
        
        result = await s3_helper.list_files('test-bucket')
        
        assert result == []
    
    @pytest.mark.asyncio
    async def test_list_files_no_such_bucket(self, s3_helper):
        """Test file listing with non-existent bucket."""
        error_response = {
            'Error': {
                'Code': 'NoSuchBucket',
                'Message': 'The specified bucket does not exist'
            }
        }
        
        s3_helper.s3_client = MagicMock()
        s3_helper.s3_client.list_objects_v2.side_effect = ClientError(error_response, 'ListObjectsV2')
        
        with pytest.raises(RuntimeError) as exc_info:
            await s3_helper.list_files('nonexistent-bucket')
        
        assert "does not exist" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_list_files_access_denied(self, s3_helper):
        """Test file listing with access denied."""
        error_response = {
            'Error': {
                'Code': 'AccessDenied',
                'Message': 'Access denied'
            }
        }
        
        s3_helper.s3_client = MagicMock()
        s3_helper.s3_client.list_objects_v2.side_effect = ClientError(error_response, 'ListObjectsV2')
        
        with pytest.raises(RuntimeError) as exc_info:
            await s3_helper.list_files('test-bucket')
        
        assert "Access denied" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_list_files_no_client(self, s3_helper):
        """Test file listing without S3 client."""
        s3_helper.s3_client = None
        
        with pytest.raises(RuntimeError) as exc_info:
            await s3_helper.list_files('test-bucket')
        
        assert "S3 client not initialized" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_validate_s3_path_object_exists(self, s3_helper):
        """Test S3 path validation for existing object."""
        mock_response = {
            'ContentLength': 1024,
            'LastModified': datetime(2024, 1, 1, 12, 0, 0),
            'ContentType': 'application/json'
        }
        
        s3_helper.s3_client = MagicMock()
        s3_helper.s3_client.head_object.return_value = mock_response
        
        result = await s3_helper.validate_s3_path('s3://test-bucket/data/file.json')
        
        assert result['valid'] is True
        assert result['type'] == 'object'
        assert result['bucket'] == 'test-bucket'
        assert result['key'] == 'data/file.json'
        assert result['size'] == 1024
        assert result['content_type'] == 'application/json'
    
    @pytest.mark.asyncio
    async def test_validate_s3_path_prefix(self, s3_helper):
        """Test S3 path validation for prefix (wildcard)."""
        mock_response = {
            'Contents': [
                {'Key': 'data/file1.json'},
                {'Key': 'data/file2.json'}
            ]
        }
        
        s3_helper.s3_client = MagicMock()
        s3_helper.s3_client.list_objects_v2.return_value = mock_response
        
        result = await s3_helper.validate_s3_path('s3://test-bucket/data/*')
        
        assert result['valid'] is True
        assert result['type'] == 'prefix'
        assert result['bucket'] == 'test-bucket'
        assert result['prefix'] == 'data/'
        assert len(result['sample_objects']) == 2
    
    @pytest.mark.asyncio
    async def test_validate_s3_path_object_not_found(self, s3_helper):
        """Test S3 path validation for non-existent object."""
        error_response = {
            'Error': {'Code': '404', 'Message': 'Not Found'}
        }
        
        s3_helper.s3_client = MagicMock()
        s3_helper.s3_client.head_object.side_effect = ClientError(error_response, 'HeadObject')
        
        result = await s3_helper.validate_s3_path('s3://test-bucket/nonexistent.json')
        
        assert result['valid'] is False
        assert "Object not found" in result['error']
    
    @pytest.mark.asyncio
    async def test_validate_s3_path_invalid_format(self, s3_helper):
        """Test S3 path validation with invalid format."""
        s3_helper.s3_client = MagicMock()
        
        result = await s3_helper.validate_s3_path('invalid-path')
        
        assert result['valid'] is False
        assert "Invalid S3 path format" in result['error']
    
    @pytest.mark.asyncio
    async def test_validate_s3_path_no_client(self, s3_helper):
        """Test S3 path validation without client."""
        s3_helper.s3_client = None
        
        result = await s3_helper.validate_s3_path('s3://test-bucket/file.json')
        
        assert result['valid'] is False
        assert "S3 client not initialized" in result['error']
    
    def test_parse_s3_path(self, s3_helper):
        """Test S3 URL parsing."""
        bucket, key = s3_helper._parse_s3_path('s3://test-bucket/path/to/file.json')
        assert bucket == 'test-bucket'
        assert key == 'path/to/file.json'
        
        bucket, key = s3_helper._parse_s3_path('s3://bucket-only')
        assert bucket == 'bucket-only'
        assert key == ''
        
        bucket, key = s3_helper._parse_s3_path('invalid-url')
        assert bucket is None
        assert key is None
    
    @pytest.mark.asyncio
    async def test_get_bucket_info_success(self, s3_helper):
        """Test getting bucket information successfully."""
        s3_helper.s3_client = MagicMock()
        s3_helper.s3_client.head_bucket.return_value = {}
        s3_helper.s3_client.get_bucket_location.return_value = {'LocationConstraint': 'us-west-2'}
        s3_helper.s3_client.list_objects_v2.return_value = {
            'Contents': [{'Key': 'file1'}, {'Key': 'file2'}],
            'IsTruncated': False
        }
        
        result = await s3_helper.get_bucket_info('test-bucket')
        
        assert result['bucket'] == 'test-bucket'
        assert result['exists'] is True
        assert result['region'] == 'us-west-2'
        assert result['accessible'] is True
        assert '2 objects' in result['object_count']
    
    @pytest.mark.asyncio
    async def test_get_bucket_info_not_found(self, s3_helper):
        """Test getting info for non-existent bucket."""
        error_response = {
            'Error': {'Code': 'NoSuchBucket', 'Message': 'Bucket not found'}
        }
        
        s3_helper.s3_client = MagicMock()
        s3_helper.s3_client.head_bucket.side_effect = ClientError(error_response, 'HeadBucket')
        
        result = await s3_helper.get_bucket_info('nonexistent-bucket')
        
        assert result['bucket'] == 'nonexistent-bucket'
        assert result['exists'] is False
        assert "does not exist" in result['error']
    
    @pytest.mark.asyncio
    async def test_get_bucket_info_access_denied(self, s3_helper):
        """Test getting info with access denied."""
        error_response = {
            'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}
        }
        
        s3_helper.s3_client = MagicMock()
        s3_helper.s3_client.head_bucket.side_effect = ClientError(error_response, 'HeadBucket')
        
        result = await s3_helper.get_bucket_info('private-bucket')
        
        assert result['bucket'] == 'private-bucket'
        assert result['exists'] is True
        assert result['accessible'] is False
        assert "Access denied" in result['error']
    
    def test_format_file_size(self, s3_helper):
        """Test file size formatting."""
        assert s3_helper.format_file_size(0) == "0 B"
        assert s3_helper.format_file_size(1024) == "1.0 KB"
        assert s3_helper.format_file_size(1024 * 1024) == "1.0 MB"
        assert s3_helper.format_file_size(1024 * 1024 * 1024) == "1.0 GB"
        assert s3_helper.format_file_size(1536) == "1.5 KB"
    
    def test_get_s3_credentials_status_configured(self, s3_helper):
        """Test credentials status when configured."""
        with patch('boto3.client') as mock_boto_client:
            mock_sts = MagicMock()
            mock_sts.get_caller_identity.return_value = {
                'Account': '123456789012',
                'Arn': 'arn:aws:iam::123456789012:user/test'
            }
            mock_boto_client.return_value = mock_sts
            
            status = s3_helper.get_s3_credentials_status()
            
            assert status['configured'] is True
            assert status['account_id'] == '123456789012'
            assert 'test' in status['user_arn']
    
    def test_get_s3_credentials_status_not_configured(self, s3_helper):
        """Test credentials status when not configured."""
        with patch('boto3.client', side_effect=NoCredentialsError):
            status = s3_helper.get_s3_credentials_status()
            
            assert status['configured'] is False
            assert "credentials not found" in status['error']
    
    def test_get_s3_credentials_status_invalid(self, s3_helper):
        """Test credentials status when invalid."""
        error_response = {
            'Error': {'Code': 'InvalidUserID.NotFound', 'Message': 'Invalid credentials'}
        }
        
        with patch('boto3.client') as mock_boto_client:
            mock_sts = MagicMock()
            mock_sts.get_caller_identity.side_effect = ClientError(error_response, 'GetCallerIdentity')
            mock_boto_client.return_value = mock_sts
            
            status = s3_helper.get_s3_credentials_status()
            
            assert status['configured'] is False
            assert "credentials invalid" in status['error']