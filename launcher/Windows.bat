@echo off
chcp 65001 >nul
title Kino Bot - Launcher
setlocal

REM launcher/ ichidan loyiha ildiziga o'tamiz
cd /d "%~dp0.."

:menu
cls
echo ==================================================
echo                 KINO BOT  -  LAUNCHER
echo ==================================================
echo  Loyiha: %cd%
echo.
echo   [1] Ishga tushirish   (build + start + loglar)
echo   [2] Loglarni ko'rish  (bot)
echo   [3] Holat             (status)
echo   [4] Qayta ishga tushirish (restart)
echo   [5] To'xtatish        (stop)
echo   [6] To'liq o'chirish  (down)
echo   [7] Chiqish
echo ==================================================
set "choice="
set /p "choice=Tanlang [1-7]: "

if "%choice%"=="1" goto start
if "%choice%"=="2" goto logs
if "%choice%"=="3" goto status
if "%choice%"=="4" goto restart
if "%choice%"=="5" goto stop
if "%choice%"=="6" goto down
if "%choice%"=="7" goto end
goto menu

:check_docker
docker info >nul 2>&1
if errorlevel 1 (
    echo.
    echo [XATO] Docker ishlamayapti.
    echo        Docker Desktop'ni ishga tushiring va tayyor bo'lguncha kuting.
    echo.
    pause
    exit /b 1
)
exit /b 0

:start
call :check_docker || goto menu
if not exist ".env" (
    echo.
    echo [!] .env topilmadi - .env.example dan nusxa olinmoqda...
    copy ".env.example" ".env" >nul
    echo [!] .env yaratildi.
    echo     Ichidagi BOT_TOKEN, ADMIN_IDS, STORAGE_CHANNEL_ID, REQUIRED_CHANNELS
    echo     qiymatlarini to'ldiring, keyin qaytadan [1] ni tanlang.
    echo.
    notepad ".env"
    pause
    goto menu
)
echo.
echo [*] Konteynerlar qurilmoqda va ishga tushmoqda (birinchi marta bir necha daqiqa)...
docker compose up -d --build
if errorlevel 1 (
    echo.
    echo [XATO] Ishga tushmadi. Yuqoridagi xabarlarni tekshiring.
    echo.
    pause
    goto menu
)
echo.
echo [OK] Ishga tushdi. Konteynerlar holati:
docker compose ps
echo.
echo [i] Endi bot loglari ko'rsatiladi. Loglardan chiqish uchun: Ctrl+C
echo     (Konteynerlar orqa fonda ishlab turaveradi.)
echo.
timeout /t 3 >nul
docker compose logs -f bot
goto menu

:logs
call :check_docker || goto menu
echo.
echo [i] Loglardan chiqish uchun: Ctrl+C
echo.
docker compose logs -f bot
goto menu

:status
call :check_docker || goto menu
echo.
docker compose ps
echo.
pause
goto menu

:restart
call :check_docker || goto menu
echo.
echo [*] Qayta ishga tushirilmoqda...
docker compose restart
echo.
docker compose ps
echo.
pause
goto menu

:stop
call :check_docker || goto menu
echo.
echo [*] To'xtatilmoqda...
docker compose stop
echo.
echo [OK] To'xtatildi (ma'lumotlar saqlanadi).
echo.
pause
goto menu

:down
call :check_docker || goto menu
echo.
echo [*] Konteynerlar o'chirilmoqda (ma'lumotlar bazasi saqlanib qoladi)...
docker compose down
echo.
echo [OK] O'chirildi.
echo.
pause
goto menu

:end
endlocal
exit /b 0
