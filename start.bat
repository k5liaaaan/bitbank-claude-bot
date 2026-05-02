@echo off
chcp 65001 > NUL
echo.
echo  ========================================
echo   BTC Auto Trader - 起動中...
echo  ========================================
echo.

REM .env チェック
if not exist .env (
    echo  .env ファイルが見つかりません。
    echo  .env.example からコピーします...
    copy .env.example .env > NUL
    echo.
    echo  ======================================================
    echo   .env を開いて APIキーを設定してから再度実行してください。
    echo  ======================================================
    echo.
    start notepad .env
    pause
    exit /b 1
)

REM Docker Desktop チェック
docker info > NUL 2>&1
if %ERRORLEVEL% neq 0 (
    echo  [エラー] Docker Desktop が起動していません。
    echo  Docker Desktop を起動してから再度実行してください。
    echo  https://www.docker.com/products/docker-desktop/
    pause
    exit /b 1
)

echo  Docker コンテナを起動しています...
docker compose up -d --build

if %ERRORLEVEL% neq 0 (
    echo  [エラー] コンテナの起動に失敗しました。
    pause
    exit /b 1
)

echo  サーバーの起動を待機しています...
:wait_loop
timeout /t 2 /nobreak > NUL
curl -s http://localhost:8080/api/health > NUL 2>&1
if %ERRORLEVEL% neq 0 goto wait_loop

echo.
echo  ========================================
echo   起動完了！ブラウザを開きます...
echo  ========================================
echo.
echo  URL: http://localhost:8080
echo  停止: docker compose down
echo.

start http://localhost:8080
pause
