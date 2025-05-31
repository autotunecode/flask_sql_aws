## Cursor Agent向け要件定義書：画像・メタデータ管理APIサンプルアプリ

### 1. 目的

本要件定義書は、指定された技術スタックと要件に基づき、画像ファイルとその関連メタデータを保存・管理するシンプルなAPIアプリケーションのローカル実行可能なサンプル実装をCursor Agentに指示することを目的とします。

### 2. アプリケーション概要

ユーザーが画像ファイルと付随するメタデータをアップロードできるAPIアプリケーションを構築します。アップロードされた画像はAWS S3（ローカルではMinIO）、メタデータはPostgreSQLに保存されます。重複画像のアップロードはスキップされ、APIキーによる認証を必須とします。

### 3. 機能要件

#### 3.1. 画像・メタデータアップロードAPI

*   **エンドポイント:** `/api/upload` (POSTメソッド)
*   **リクエスト:**
    *   `multipart/form-data` 形式で画像ファイル (`image_file`として) を受け取る。
    *   `application/json` 形式でメタデータ (`metadata`としてJSON文字列) を受け取る。メタデータには少なくとも `title` (string) と `description` (string) を含む。
*   **処理内容:**
    1.  APIキー認証を実行する。
    2.  受信した画像ファイルのMD5ハッシュ値を計算する。
    3.  PostgreSQLデータベースに、このハッシュ値を持つデータが既に存在するか確認する。
    4.  **重複画像のスキップ:** 既に同じハッシュ値の画像が存在する場合は、保存処理を行わず、適切なエラーレスポンス（例: "Image already exists"）を返す。
    5.  重複しない場合、画像ファイルをS3（ローカルではMinIO）に保存する。S3のキーはハッシュ値や一意のIDを使用。
    6.  PostgreSQLに、以下のメタデータを保存する：
        *   画像ID (一意のID)
        *   S3パス/キー
        *   画像のMD5ハッシュ値
        *   元のファイル名
        *   MIMEタイプ
        *   ファイルサイズ
        *   アップロード日時 (UTC)
        *   `title` (ユーザー入力)
        *   `description` (ユーザー入力)
        *   （オプション）Gemini APIによる画像分析結果 (後述の考慮事項を参照)
*   **レスポンス:**
    *   成功時: 保存された画像ID、S3パス、その他関連メタデータをJSON形式で返す (HTTP 201 Created)。
    *   失敗時: エラーメッセージをJSON形式で返す (HTTP 400 Bad Request, 401 Unauthorized, 409 Conflictなど)。

#### 3.2. APIキー認証

*   すべてのAPIエンドポイントに対してAPIキー認証を必須とする。
*   クライアントはリクエストヘッダーに `X-API-Key: YOUR_API_KEY` を含めること。
*   有効なAPIキーは環境変数 (`API_KEY`) から取得し、それと照合する。
*   無効なAPIキーの場合は、HTTP 401 Unauthorized エラーを返す。

### 4. 非機能要件 (技術スタック・環境)

*   **API開発言語・フレームワーク:** Python 3.x, Flask
*   **データベース:** PostgreSQL
    *   永続化のため、Docker Volumeを使用すること。
    *   テーブルスキーマは必要に応じて定義（`id`, `s3_key`, `md5_hash`, `original_filename`, `mimetype`, `filesize`, `uploaded_at`, `title`, `description` など）。
*   **オブジェクトストレージ:** AWS S3
    *   ローカル環境での実行・評価のため、`docker-compose` で **MinIO** コンテナを構築し、S3互換エンドポイントとして利用する。
    *   本番運用はAWS S3を想定したAWS SDK (`boto3`) の利用を推奨。
*   **コンテナ化:**
    *   `Dockerfile` を提供し、Flaskアプリケーションをコンテナ化する。
    *   `docker-compose.yml` を作成し、Flaskアプリケーション、PostgreSQL、MinIOコンテナを連携させ、`docker-compose up` で一括起動可能にすること。
*   **環境変数:**
    *   DB接続情報 (`POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `DB_HOST`)
    *   MinIO接続情報 (`MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, `MINIO_ENDPOINT_URL`, `MINIO_BUCKET_NAME`)
    *   APIキー (`API_KEY`)
    *   これらの情報は`.env`ファイルや`docker-compose.yml`で設定できるようにする。
*   **本番運用考慮:**
    *   AWS ECS (Fargate) での運用を想定したシンプルな設計とする（ログ出力、設定管理）。
    *   （ECS Fargate特有の設定はサンプルアプリの範囲外とするが、将来の移行を妨げない設計。）

### 5. アプリケーションコンテンツ（Cursor Agentへの指示）

*   **プロジェクト構造:**
    *   `app/` (Flaskアプリケーションコード)
        *   `app.py` (メインのFlaskアプリケーション、APIエンドポイント定義)
        *   `db.py` (DB接続、モデル定義、CRUD操作)
        *   `s3_utils.py` (S3/MinIO操作)
        *   `auth.py` (APIキー認証ロジック)
        *   `config.py` (設定情報)
    *   `docker-compose.yml`
    *   `Dockerfile`
    *   `requirements.txt`
    *   `init_db.sql` (PostgreSQLのDDL/DML、テーブル作成スクリプト)
    *   `README.md`

*   **README.md に含めるべき内容:**
    *   セットアップ手順 (`docker-compose` を用いた起動方法)
    *   APIの利用方法（エンドポイント、リクエスト例、レスポンス例、APIキーの指定方法）
    *   MinIOのWeb UIへのアクセス方法 (もしあれば)
    *   PostgreSQLへの接続方法 (任意)

### 6. 考慮事項・制約

*   **Gemini APIの利用:** 今回の要件では必須ではありませんが、将来的な拡張性を考慮し、`gemini-python`などのライブラリを`requirements.txt`に含めるか、関連機能を実装する余地を残すこと。例えば、アップロード時にGemini APIで画像の内容を簡単なテキストとして分析し、その結果をメタデータ（PostgreSQL）に保存する機能を追加しても良い。その場合、APIキーを環境変数で設定可能にすること。
*   **エラーハンドリング:** サンプルアプリのため、基本的なエラーハンドリングで問題ありません。
*   **ファイルサイズの制限:** アップロードする画像ファイルの最大サイズは適宜設定（例: 5MB）。

### 7. 提出物

*   GitHubリポジトリ形式でソースコード一式
*   `docker-compose.yml`
*   `README.md`
*   `init_db.sql`