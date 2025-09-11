# NVMe/SSD Erasure Report Builder

Generates compliance-ready reports for NVMe/SSD secure erasures using `nvme format` command.

## Quick Start

1. **Download and setup:**
   ```bash
   wget https://github.com/sambilbow/nvme-format-report/archive/refs/heads/main.zip
   unzip main.zip
   cd nvme-format-report-main
   sudo apt update && sudo apt install -y curl
   ./scripts/bootstrap.sh
   exec bash
   ```

2. **Use the tool:**
   ```bash
   mise run setup          # One-time setup
   mise run collect        # Phase 1: Collect device info
   mise run execute        # Phase 2: Erase and generate reports
   ```

## What It Does

- Collects device information (model, serial, capacity)
- Executes `nvme format` with secure erase settings
- Verifies the erase was successful
- Lets you choose which report formats to generate (TXT, HTML, PDF, JSON)

## ⚠️ Important

- **DESTRUCTIVE**: This tool permanently erases all data on target devices
- **Review first**: Always check device paths before running
- **Reports contain sensitive data**: Review before sharing publicly

## Requirements

- Ubuntu/Debian system
- NVMe device to erase
- Internet connection for initial setup

## Output

Reports are saved in the `build/` directory with timestamps and device identifiers.