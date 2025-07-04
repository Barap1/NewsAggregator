@echo off
echo Setting up Gemini API Key...
echo.
set /p API_KEY="Enter your Gemini API Key: "
setx GEMINI_API_KEY "%API_KEY%"
echo.
echo API Key has been set as environment variable GEMINI_API_KEY
echo Please restart your terminal/command prompt for the changes to take effect.
pause
