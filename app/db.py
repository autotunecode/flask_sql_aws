import psycopg2
import psycopg2.pool
from datetime import datetime
import uuid
import logging
from .config import Config

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        self.connection_pool = None
        self._init_connection_pool()
    
    def _init_connection_pool(self):
        """データベース接続プールを初期化"""
        try:
            self.connection_pool = psycopg2.pool.SimpleConnectionPool(
                1, 20,
                host=Config.DB_HOST,
                database=Config.POSTGRES_DB,
                user=Config.POSTGRES_USER,
                password=Config.POSTGRES_PASSWORD,
                port=5432
            )
            logger.info("Database connection pool initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database connection pool: {e}")
            raise
    
    def get_connection(self):
        """接続プールから接続を取得"""
        return self.connection_pool.getconn()
    
    def put_connection(self, conn):
        """接続をプールに戻す"""
        self.connection_pool.putconn(conn)
    
    def check_image_exists(self, md5_hash):
        """MD5ハッシュで重複画像をチェック"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT id, s3_key, title, description FROM images WHERE md5_hash = %s",
                (md5_hash,)
            )
            
            result = cursor.fetchone()
            cursor.close()
            
            if result:
                return {
                    'id': result[0],
                    's3_key': result[1],
                    'title': result[2],
                    'description': result[3]
                }
            return None
            
        except Exception as e:
            logger.error(f"Error checking image existence: {e}")
            raise
        finally:
            if conn:
                self.put_connection(conn)
    
    def save_image_metadata(self, s3_key, md5_hash, original_filename, 
                          mimetype, filesize, title, description, gemini_analysis=None):
        """画像メタデータをデータベースに保存"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            image_id = str(uuid.uuid4())
            uploaded_at = datetime.utcnow()
            
            cursor.execute("""
                INSERT INTO images (
                    id, s3_key, md5_hash, original_filename, mimetype, 
                    filesize, uploaded_at, title, description, gemini_analysis
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                image_id, s3_key, md5_hash, original_filename, mimetype,
                filesize, uploaded_at, title, description, gemini_analysis
            ))
            
            result = cursor.fetchone()
            conn.commit()
            cursor.close()
            
            return {
                'id': result[0],
                's3_key': s3_key,
                'md5_hash': md5_hash,
                'original_filename': original_filename,
                'mimetype': mimetype,
                'filesize': filesize,
                'uploaded_at': uploaded_at.isoformat(),
                'title': title,
                'description': description,
                'gemini_analysis': gemini_analysis
            }
            
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Error saving image metadata: {e}")
            raise
        finally:
            if conn:
                self.put_connection(conn)

# グローバルなデータベースマネージャーインスタンス
db_manager = DatabaseManager() 