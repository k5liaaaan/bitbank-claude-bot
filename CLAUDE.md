# bitbank-claude-bot プロジェクト概要

## このプロジェクトについて
bitbank APIとClaude AIを使ったBTC/JPY自動取引ツール。
Docker環境で動作し、Mac/Windows両対応。

## 設計書
詳細は [docs/設計書.md](docs/設計書.md) を参照。

## 確定している技術スタック
- **コンテナ**: Docker / docker compose
- **バックエンド**: Python 3.12 / FastAPI
- **DB**: SQLite（1年自動パージ）
- **キャッシュ・pub/sub**: Redis 7
- **フロントエンド**: HTML / CSS / Vanilla JS（npm不要）
- **チャート**: Chart.js (CDN)
- **Claude SDK**: anthropic Python SDK（プロンプトキャッシュ有効化済み）
- **Claudeモデル**: claude-sonnet-4-6
- **bitbank SDK**: python-bitbankcc

## 確定している仕様
- 取引ペア: BTC/JPY のみ
- 起動: `start.bat`（Windows）/ `start.sh`（Mac）ダブルクリックまたは実行
- UI: ダーク系リッチデザイン、WebSocketでリアルタイム更新
- ドライランモード: デフォルトON（DRY_RUN=true）。本番移行はユーザーが手動でOFF
- Claudeの役割: 売買シグナル判断のみ。注文量・損切りは固定値
- ポーリング間隔: 15分（Claude API呼び出し）
- グローバルストップ: ブラウザUIで基準資産額と損失率を手動設定
- ログ・取引履歴保存期間: 1年
- OS通知: なし（ブラウザUIで確認）

## ディレクトリ構成（予定）
```
bitbank-claude-bot/
├── docs/設計書.md         # 設計書
├── src/
│   ├── server/            # Python FastAPI（Dockerコンテナ）
│   └── web/               # フロントエンド（HTML/CSS/JS）
├── config/trading_rules.md  # 取引ルール（ユーザー編集）
├── data/                  # SQLite（gitignore）
├── .env                   # APIキー（gitignore）
├── .env.example
├── docker-compose.yml
├── start.bat / start.sh
└── CLAUDE.md              # このファイル
```

## 取引ルールMD構造
`config/trading_rules.md` にユーザーが記述。
固定見出し: `## 基本設定` `## リスク管理` `## Claudeへの取引指示` `## 買いシグナル（参考）` `## 売りシグナル（参考）` `## 取引禁止時間帯`

## セキュリティ上の注意
- `.env` は絶対にgitにコミットしない（.gitignoreで除外済み）
- サーバーは `127.0.0.1` にのみバインド（外部非公開）
- bitbank APIキーには最小限の権限のみ付与

## 実装の進め方（今後のタスク）
1. docker-compose.yml + Dockerfile（インフラ基盤）
2. FastAPI サーバー骨格（ヘルスチェック・静的ファイル配信）
3. bitbank APIクライアント（価格取得・残高・注文）
4. Redis連携・WebSocket（リアルタイム配信）
5. 取引エンジン（Claude連携・グローバルストップ）
6. ブラウザUI（ダッシュボード・設定画面）
7. start.bat / start.sh 起動スクリプト

## GitHub
https://github.com/k5liaaaan/bitbank-claude-bot

## 開発者メモ
- ユーザーはエンジニアではない可能性があるため、起動方法はダブルクリックで完結させる
- 他の人もGitからクローンして使えることを想定（各自の.envでAPIキー管理）
