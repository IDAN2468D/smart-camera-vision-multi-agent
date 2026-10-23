@echo off
title Push to GitHub - Smart Camera Vision Multi-Agent
echo ===============================================================
echo 🚀 PUSHING REPOSITORY TO GITHUB (IDAN2468D)
echo 📦 Target: https://github.com/IDAN2468D/smart-camera-vision-multi-agent
echo ===============================================================
echo.

git push -u origin main

if %errorlevel% neq 0 (
    echo.
    echo ⚠️ Push failed: The repository was not found on GitHub yet.
    echo Please make sure you created the empty repository at:
    echo https://github.com/new with name: smart-camera-vision-multi-agent
    echo.
) else (
    echo.
    echo ✅ SUCCESS! All code and GitHub Actions CI/CD have been pushed!
    echo 🌐 Repository URL: https://github.com/IDAN2468D/smart-camera-vision-multi-agent
    echo.
)
pause
