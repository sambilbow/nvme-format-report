#!/bin/bash
set -euo pipefail

echo "🚀 Starting NVMe Format Report Bootstrap"
echo "========================================"

# Install gum
echo "📦 Installing gum and dependencies..."
echo "DEBUG: Creating apt keyrings directory"
sudo mkdir -p /etc/apt/keyrings

echo "DEBUG: Downloading charm GPG key"
curl -fsSL https://repo.charm.sh/apt/gpg.key | sudo gpg --dearmor -o /etc/apt/keyrings/charm.gpg

echo "DEBUG: Adding charm repository"
echo "deb [signed-by=/etc/apt/keyrings/charm.gpg] https://repo.charm.sh/apt/ * *" | sudo tee /etc/apt/sources.list.d/charm.list

echo "DEBUG: Updating package lists"
sudo apt update

echo "DEBUG: Installing packages: gum curl git"
sudo apt install -y gum curl git

echo "✅ Gum installation completed"

# Install mise
echo "🐍 Installing mise..."
echo "DEBUG: Downloading mise installer"
curl https://mise.run/bash | sh

echo "DEBUG: Sourcing bashrc"
source ~/.bashrc

echo "✅ Mise installation completed"

# Clone the repository
echo "📁 Cloning repository..."
echo "DEBUG: Cloning from https://github.com/sambilbow/nvme-format-report.git"
git clone https://github.com/sambilbow/nvme-format-report.git

echo "DEBUG: Changing to repository directory"
cd nvme-format-report

echo "DEBUG: Running mise setup"
mise setup

echo "✅ Bootstrap completed successfully!"
echo "📁 You are now in: $(pwd)"
echo "🔧 Next steps:"
echo "   1. Run: mise run setup"
echo "   2. Follow the workflow in the README"