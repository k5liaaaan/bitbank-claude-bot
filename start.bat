@echo off
echo.
echo  ========================================
echo   BTC Auto Trader - Starting...
echo  ========================================
echo.

if not exist .env (
    echo  .env not found. Copying from .env.example...
    copy .env.example .env > NUL
    echo.
    echo  Please edit .env and set your API keys, then run start.bat again.
    echo.
    start "" notepad .env
    pause
    exit /b 1
)

docker info > NUL 2>&1
if %ERRORLEVEL% neq 0 (
    echo  [ERROR] Docker Desktop is not running.
    echo  Please start Docker Desktop and try again.
    pause
    exit /b 1
)

echo  Starting Docker containers...
docker compose up -d --build
if %ERRORLEVEL% neq 0 (
    echo.
    echo  [ERROR] Failed to start containers.
    docker compose logs --tail=40
    pause
    exit /b 1
)

echo  Waiting for server to be ready...
set RETRY=0
:wait_loop
set /a RETRY+=1
if %RETRY% gtr 30 (
    echo.
    echo  [ERROR] Server did not start within 60 seconds.
    docker compose ps
    docker compose logs --tail=40 api
    pause
    exit /b 1
)
timeout /t 2 /nobreak > NUL
curl -sf http://localhost:8080/api/health > NUL 2>&1
if %ERRORLEVEL% neq 0 goto wait_loop

echo.
docker compose ps
echo.
echo  ========================================
echo   Ready! Opening browser...
echo   URL  : http://localhost:8080
echo   Stop : docker compose down
echo  ========================================
echo.
start http://localhost:8080
pause
