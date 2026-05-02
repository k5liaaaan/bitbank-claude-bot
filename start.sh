#!/bin/bash
set -e

echo ""
echo " ========================================"
echo "  BTC Auto Trader - 起動中..."
echo " ========================================"
echo ""

# .env チェック
if [ ! -f .env ]; then
    echo " .env ファイルが見つかりません。"
    echo " .env.example からコピーします..."
    cp .env.example .env
    echo ""
    echo " ======================================================"
    echo "  .env を開いて APIキーを設定してから再度実行してください。"
    echo " ======================================================"
    echo ""
    exit 1
fi

# Docker Desktop チェック
if ! docker info > /dev/null 2>&1; then
    echo " [エラー] Docker Desktop が起動していません。"
    echo " Docker Desktop を起動してから再度実行してください。"
    exit 1
fi

echo " Docker コンテナを起動しています..."
docker compose up -d --build

echo " サーバーの起動を待機しています..."
for i in $(seq 1 30); do
    if curl -s http://localhost:8080/api/health > /dev/null 2>&1; then
        break
    fi
    sleep 2
done

echo ""
echo " ========================================"
echo "  起動完了！ブラウザを開きます..."
echo " ========================================"
echo ""
echo " URL: http://localhost:8080"
echo " 停止: docker compose down"
echo ""

# ブラウザを開く（macOS / Linux）
if command -v open &> /dev/null; then
    open http://localhost:8080
elif command -v xdg-open &> /dev/null; then
    xdg-open http://localhost:8080
fi
