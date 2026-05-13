@echo off
echo ============================================
echo   DeskTracking Backend - Server Management
echo ============================================
echo.
echo Connecting to server...
echo After login, paste these commands one by one:
echo.
echo   cd /var/www/desktracking/backend
echo   source venv/bin/activate
echo   pm2 start /var/www/desktracking/ecosystem.config.js
echo   pm2 save
echo   pm2 status
echo.
echo ============================================
echo.
ssh root@69.62.76.202
