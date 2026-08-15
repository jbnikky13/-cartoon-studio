#!/usr/bin/env bash
set -e
BLENDER_PATH="${BLENDER_PATH:-blender}"
"$BLENDER_PATH" --background --python blender/engine.py -- projects/scene.json output/cartoon.mp4
