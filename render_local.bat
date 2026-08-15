@echo off
setlocal
if "%BLENDER_PATH%"=="" set "BLENDER_PATH=blender"
%BLENDER_PATH% --background --python blender\engine.py -- projects\scene.json output\cartoon.mp4
pause
