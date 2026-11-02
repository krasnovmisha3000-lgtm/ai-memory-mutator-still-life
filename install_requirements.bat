@echo off
echo ===================================================
echo   Installing AI Memory Mutator: Python Dependencies
echo ===================================================
pip install customtkinter diffusers transformers torch pillow requests accelerate

echo.
echo ===================================================
echo   Downloading Ollama Vision Model (Llava)
echo ===================================================
echo Checking for Ollama...
ollama run llava

echo.
echo ===================================================
echo   Setup Complete! You can now run python ai_app.py
echo ===================================================
pause
