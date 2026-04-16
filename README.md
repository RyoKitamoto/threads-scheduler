# threads-scheduler

Threads 予約投稿を GitHub Actions で自動公開するシステム。

## 仕組み

1. scheduled_posts.json に投稿コンテナIDと予定時刻を記録
2. GitHub Actions が5分ごとに実行
3. 予定時刻を過ぎた pending 投稿を自動公開
4. 公開後 scheduled_posts.json のステータスを published に更新

## 設定

GitHub Secrets に以下を設定:
- THREADS_ACCESS_TOKEN : Threads APIアクセストークン
- THREADS_USER_ID : Threads ユーザーID (26577900168506682)
