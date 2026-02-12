#!/bin/bash
# Setup script for memU + Gemini CLI OAuth via CLIProxyAPI

echo "============================================"
echo " memU + Gemini CLI OAuth Setup Script"
echo "============================================"
echo ""

# Check if CLIProxyAPI is installed
if ! command -v cli-proxy-api &> /dev/null; then
    echo "❌ CLIProxyAPI not found. Installing..."

    # Try Homebrew first
    if command -v brew &> /dev/null; then
        echo "📦 Installing via Homebrew..."
        brew install cliproxyapi
    else
        echo "📦 Installing manually..."
        # Download and install
        ARCH=$(uname -m)
        if [ "$ARCH" = "arm64" ]; then
            curl -L -o /tmp/cli-proxy-api.tar.gz https://github.com/router-for-me/CLIProxyAPI/releases/latest/download/cli-proxy-api_Darwin_arm64.tar.gz
        else
            curl -L -o /tmp/cli-proxy-api.tar.gz https://github.com/router-for-me/CLIProxyAPI/releases/latest/download/cli-proxy-api_Darwin_x86_64.tar.gz
        fi

        tar -xzf /tmp/cli-proxy-api.tar.gz -C /tmp/
        sudo mv /tmp/cli-proxy-api /usr/local/bin/
        sudo chmod +x /usr/local/bin/cli-proxy-api
    fi

    echo "✅ CLIProxyAPI installed successfully"
else
    echo "✅ CLIProxyAPI already installed"
fi

# Create config directory
mkdir -p ~/.cli-proxy-api

# Create configuration file if it doesn't exist
if [ ! -f ~/.cli-proxy-api/config.yaml ]; then
    echo "📝 Creating configuration file..."
    cat > ~/.cli-proxy-api/config.yaml << 'EOF'
# CLIProxyAPI Configuration for Gemini CLI OAuth

# Gemini CLI Provider (OAuth authentication)
gemini-cli:
  enabled: true

# Server configuration
server:
  port: 8317
  host: "127.0.0.1"

# OpenAI API compatibility mode
openai-compatibility:
  enabled: true
EOF
    echo "✅ Configuration file created at ~/.cli-proxy-api/config.yaml"
else
    echo "✅ Configuration file already exists"
fi

echo ""
echo "============================================"
echo "📋 Next Steps:"
echo "============================================"
echo ""
echo "1. Start CLIProxyAPI:"
echo "   cli-proxy-api"
echo ""
echo "2. Authenticate with Gemini (OAuth):"
echo "   cli-proxy-api --login"
echo ""
echo "   This will open a browser for Google OAuth."
echo "   Login with your Google account."
echo ""
echo "3. Once authenticated, CLIProxyAPI will run on:"
echo "   http://127.0.0.1:8317"
echo ""
echo "4. Configure memU to use the proxy:"
echo "   base_url: http://127.0.0.1:8317"
echo "   api_key: sk-dummy"
echo ""
echo "5. Test the connection:"
echo "   See example: examples/gemini_cli_memu_example.py"
echo ""
echo "============================================"
echo "✨ Gemini CLI OAuth + memU Ready!"
echo "============================================"
