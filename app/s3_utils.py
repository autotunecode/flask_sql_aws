import boto3
from botocore.exceptions import ClientError, NoCredentialsError
import logging
import time
from .config import Config

logger = logging.getLogger(__name__)

class S3Manager:
    def __init__(self):
        self.s3_client = None
        self._init_s3_client()
    
    def _init_s3_client(self):
        """S3/MinIOクライアントを初期化"""
        try:
            self.s3_client = boto3.client(
                's3',
                endpoint_url=Config.MINIO_ENDPOINT_URL,
                aws_access_key_id=Config.MINIO_ACCESS_KEY,
                aws_secret_access_key=Config.MINIO_SECRET_KEY,
                region_name='us-east-1'  # MinIOでは任意のリージョン
            )
            
            # バケットが存在するかチェック、なければ作成（リトライ付き）
            self._ensure_bucket_exists()
            logger.info("S3 client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize S3 client: {e}")
            raise
    
    def _ensure_bucket_exists(self):
        """バケットの存在を確認し、なければ作成（競合状態を適切に処理）"""
        max_retries = 5
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                # まずバケットの存在確認
                self.s3_client.head_bucket(Bucket=Config.MINIO_BUCKET_NAME)
                logger.info(f"Bucket {Config.MINIO_BUCKET_NAME} already exists")
                return
                
            except ClientError as e:
                error_code = int(e.response['Error']['Code'])
                if error_code == 404:
                    # バケットが存在しない場合は作成を試行
                    try:
                        self.s3_client.create_bucket(Bucket=Config.MINIO_BUCKET_NAME)
                        logger.info(f"Created bucket {Config.MINIO_BUCKET_NAME}")
                        return
                        
                    except ClientError as create_error:
                        error_code = create_error.response.get('Error', {}).get('Code', '')
                        
                        if error_code in ['BucketAlreadyExists', 'BucketAlreadyOwnedByYou']:
                            # バケットが既に存在する場合は正常とみなす
                            logger.info(f"Bucket {Config.MINIO_BUCKET_NAME} already exists (created by another process)")
                            return
                        else:
                            logger.warning(f"Attempt {attempt + 1}/{max_retries} failed to create bucket: {create_error}")
                            if attempt < max_retries - 1:
                                time.sleep(retry_delay)
                                retry_delay *= 2  # 指数バックオフ
                            else:
                                logger.error(f"Failed to create bucket after {max_retries} attempts")
                                raise
                else:
                    logger.error(f"Error checking bucket: {e}")
                    raise
    
    def upload_file(self, file_obj, s3_key, content_type):
        """ファイルをS3/MinIOにアップロード"""
        try:
            self.s3_client.upload_fileobj(
                file_obj,
                Config.MINIO_BUCKET_NAME,
                s3_key,
                ExtraArgs={
                    'ContentType': content_type,
                    'Metadata': {
                        'uploaded_by': 'image_api'
                    }
                }
            )
            
            logger.info(f"Successfully uploaded file to {s3_key}")
            return True
            
        except NoCredentialsError:
            logger.error("AWS credentials not found")
            raise
        except Exception as e:
            logger.error(f"Error uploading file to S3: {e}")
            raise
    
    def get_file_url(self, s3_key, expiration=3600):
        """S3オブジェクトのプリサインドURLを生成"""
        try:
            response = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': Config.MINIO_BUCKET_NAME, 'Key': s3_key},
                ExpiresIn=expiration
            )
            return response
        except Exception as e:
            logger.error(f"Error generating presigned URL: {e}")
            raise

# グローバルなS3マネージャーインスタンス
s3_manager = S3Manager() 