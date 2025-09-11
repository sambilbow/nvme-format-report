# Install gum
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://repo.charm.sh/apt/gpg.key | sudo gpg --dearmor -o /etc/apt/keyrings/charm.gpg
echo "deb [signed-by=/etc/apt/keyrings/charm.gpg] https://repo.charm.sh/apt/ * *" | sudo tee /etc/apt/sources.list.d/charm.list
sudo apt update && sudo apt install gum curl git gum

# Install mise
curl https://mise.run/bash | sh
source ~/.bashrc

# Clone the repository
git clone https://github.com/sambilbow/nvme-format-report.git

# Change to the repository directory
cd nvme-format-report
mise setup