@echo off
echo setting key
set /p API_KEY="key: "
setx GEMINI_API_KEY "%API_KEY%"
pause
