#!/bin/bash
set -euo pipefail

echo "🚀 Starting NVMe Format Report Bootstrap"
echo "========================================"

# Install gum
echo "📦 Installing gum and dependencies..."
echo "Creating apt keyrings directory"
sudo mkdir -p /etc/apt/keyrings

echo "Downloading charm GPG key"
curl -fsSL https://repo.charm.sh/apt/gpg.key | sudo gpg --dearmor -o /etc/apt/keyrings/charm.gpg

echo "Adding charm repository"
echo "deb [signed-by=/etc/apt/keyrings/charm.gpg] https://repo.charm.sh/apt/ * *" | sudo tee /etc/apt/sources.list.d/charm.list

echo "Updating package lists"
sudo apt update

echo "Installing packages: gum curl git"
sudo apt install -y gum curl git

echo "✅ Gum installation completed"

# Install mise
echo "🐍 Installing mise..."
echo "Downloading mise installer"
curl https://mise.run/bash | sh

echo "Sourcing bashrc"
source ~/.bashrc

echo "Installing Python with mise"
$HOME/.local/bin/mise install python
$HOME/.local/bin/mise use --global python

echo "✅ Mise installation completed"

# Clone the repository
echo "📁 Cloning repository..."
echo "Cloning from https://github.com/sambilbow/nvme-format-report.git"
git clone https://github.com/sambilbow/nvme-format-report.git

echo "✅ Bootstrap completed successfully!"
echo "🔧 Next steps:"
echo "   1. exec bash"
echo "   2. cd nvme-format-report"
echo "   3. Run: mise run setup"
echo "   4. Follow the workflow in the README"