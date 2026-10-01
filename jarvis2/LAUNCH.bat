@echo off
REM JARVIS 2 - AUTONOMOUS AI TRADING PLATFORM
REM Launch Script for Windows
REM Status: PRODUCTION READY

setlocal enabledelayedexpansion

echo.
echo ==========================================
echo ^>^> JARVIS 2 LAUNCH SEQUENCE
echo ==========================================
echo.

REM Check Docker
docker --version >nul 2>&1
if errorlevel 1 (
    echo ^(x^) Docker not found. Install Docker Desktop and try again.
    pause
    exit /b 1
)
echo [OK] Docker found

REM Check Docker Compose
docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo ^(x^) Docker Compose not found. Install Docker Desktop and try again.
    pause
    exit /b 1
)
echo [OK] Docker Compose found

echo.
echo ==========================================
echo ^> BUILDING DOCKER IMAGES
echo ==========================================
echo.

call docker-compose build --no-cache
if errorlevel 1 (
    echo ^(x^) Build failed. Check Docker configuration.
    pause
    exit /b 1
)

echo.
echo ==========================================
echo ^> STARTING SERVICES
echo ==========================================
echo.

call docker-compose up -d
if errorlevel 1 (
    echo ^(x^) Failed to start services.
    pause
    exit /b 1
)

echo.
echo [WAIT] Waiting for services to initialize...
timeout /t 10 /nobreak

echo.
echo ==========================================
echo [OK] JARVIS 2 IS LIVE
echo ==========================================
echo.
echo ^> Frontend:     http://localhost:3000
echo ^> Backend API:  http://localhost:8000
echo ^> API Docs:     http://localhost:8000/docs
echo ^> Database:     PostgreSQL on port 5432
echo.
echo ^> Monitoring:
echo   - Dashboard: http://localhost:3000
echo   - Status: http://localhost:8000/optimizer/status
echo   - Watch logs: docker-compose logs -f backend
echo.
echo ^> System Status:
echo   - Mode: AUTONOMOUS OPTIMIZATION
echo   - Boss Agent: ACTIVE
echo   - Cycles: Running every 5 minutes
echo   - Target: 90^%+ win rate
echo.
echo ==========================================
echo [LIVE] BEST IN CLASS AUTONOMOUS PLATFORM ACTIVE
echo ==========================================
echo.
echo ^> Keep laptop ON. Internet ON. DhanHQ token active.
echo ^> Everything else is 100^% autonomous.
echo.
echo ^> Press any key to view logs...
pause

docker-compose logs -f backend
