#!/usr/bin/env bash
# -------------------------------------------------------
# Setup script: install ffmpeg + build whisper.cpp
# Run from the memU repo root:
#   bash scripts/setup_whisper.sh
# -------------------------------------------------------
set -euo pipefail

WHISPER_DIR="$HOME/whisper.cpp"
MODEL="base.en"

echo "🔧 Shadow Voice — Dependency Setup"
echo "===================================="
echo ""

# 1. ffmpeg
if command -v ffmpeg &>/dev/null; then
    echo "✅ ffmpeg already installed: $(ffmpeg -version 2>&1 | head -1)"
else
    echo "📦 Installing ffmpeg via Homebrew..."
    brew install ffmpeg
    echo "✅ ffmpeg installed"
fi
echo ""

# 2. whisper.cpp
if [ -d "$WHISPER_DIR" ]; then
    echo "✅ whisper.cpp already cloned at $WHISPER_DIR"
else
    echo "📦 Cloning whisper.cpp..."
    git clone https://github.com/ggerganov/whisper.cpp.git "$WHISPER_DIR"
    echo "✅ Cloned"
fi
echo ""

# 3. Build
echo "🔨 Building whisper.cpp..."
cd "$WHISPER_DIR"
make -j "$(sysctl -n hw.logicalcpu 2>/dev/null || echo 4)"
echo "✅ Built"
echo ""

# 4. Download model
if [ -f "$WHISPER_DIR/models/ggml-${MODEL}.bin" ]; then
    echo "✅ Model ggml-${MODEL}.bin already downloaded"
else
    echo "📥 Downloading model: ${MODEL}..."
    bash "$WHISPER_DIR/models/download-ggml-model.sh" "$MODEL"
    echo "✅ Model downloaded"
fi
echo ""

# 5. Verify
echo "===================================="
echo "🎉 Setup complete!"
echo ""
echo "  whisper.cpp : $WHISPER_DIR"
if [ -f "$WHISPER_DIR/main" ]; then
    echo "  binary      : $WHISPER_DIR/main"
elif [ -f "$WHISPER_DIR/build/bin/whisper-cli" ]; then
    echo "  binary      : $WHISPER_DIR/build/bin/whisper-cli"
fi
echo "  model       : $WHISPER_DIR/models/ggml-${MODEL}.bin"
echo "  ffmpeg      : $(which ffmpeg)"
echo ""
echo "Next: python examples/voice_simple.py --once"
