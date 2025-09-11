#!/usr/bin/env bash
set -euo pipefail

echo "🚀 NVMe Format Report - Bootstrap Script"
echo "========================================"
echo "📦 Installing system dependencies..."
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://repo.charm.sh/apt/gpg.key | sudo gpg --dearmor -o /etc/apt/keyrings/charm.gpg
echo "deb [signed-by=/etc/apt/keyrings/charm.gpg] https://repo.charm.sh/apt/ * *" | sudo tee /etc/apt/sources.list.d/charm.list
sudo apt update -q
sudo apt install --assume-yes -q git nvme-cli gum

echo "🐍 Installing Python environment manager (mise)..."

# Install mise
curl -s https://mise.run/bash | sh -s -- -y
$HOME/.local/bin/mise install -y python && $HOME/.local/bin/mise use -g python
$HOME/.local/bin/mise trust

echo "📋 Installing Python dependencies..."
pip install -r requirements.txt

echo ""
echo "✅ Bootstrap complete!"
echo "📁 You are now in: $(pwd)"
echo "🔧 Next steps:"
echo "   1. Run: mise run setup"
echo "   2. Follow the workflow in the README"
echo ""
echo "⚠️  Remember: This tool performs DESTRUCTIVE operations on storage devices!"
echo "   Always double-check device paths before running erase commands."