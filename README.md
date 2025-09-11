# NVMe Format Report Tool

A professional tool for securely wiping NVMe devices and generating detailed reports. Designed for IT professionals, data centers, and businesses that need to securely dispose of NVMe storage devices.

## Features

- **Device Discovery**: Automatically detects and analyzes NVMe devices
- **Smart Erase Selection**: Chooses the best available erase method (crypto erase > secure erase > format)
- **Safety Checks**: Validates device availability and warns about mounted devices
- **Professional Reports**: Generates both PDF and JSON reports with business information
- **System Tracking**: Records system UUID, OS, and kernel information
- **Millisecond Precision**: Accurate timing measurements for fast operations

## Quick Start

### Prerequisites

- Linux system with NVMe devices
- `nvme-cli` tools installed
- Python 3.11+
- Mise task runner

### Bootstrap Installation

```bash
curl -fsSL https://raw.githubusercontent.com/sambilbow/nvme-format-report/main/bootstrap.sh | bash
```

### Usage

```bash
# Run complete workflow
mise dev

# Or run individual phases
mise collect  # Gather device information
mise plan     # Create execution plan
mise execute  # Perform wipe operation
mise report   # Generate reports
```

## Workflow

1. **Collect**: Discovers NVMe devices and gathers system information
2. **Plan**: Creates execution plan based on device capabilities
3. **Execute**: Performs the secure wipe operation
4. **Report**: Generates professional PDF and JSON reports

## Safety Features

- Device validation before operations
- Mount detection and warnings
- User confirmation for destructive operations
- Comprehensive error handling
- Detailed logging and state tracking

## Reports

Reports are generated in the `build/` directory with timestamps:
- `wipe_report_YYYYMMDD_HHMMSS.pdf` - Professional PDF report
- `wipe_report_YYYYMMDD_HHMMSS.json` - Machine-readable JSON data

## Configuration

Edit `.env` file with your business information:
```bash
BUSINESS_NAME=Your Company Name
BUSINESS_ADDRESS=123 Main St, City, State 12345
BUSINESS_CONTACT=John Doe
BUSINESS_PHONE=+1-555-123-4567
BUSINESS_EMAIL=contact@yourcompany.com
BUSINESS_WEBSITE=https://yourcompany.com
TECHNICIAN_NAME=Jane Doe
```

## Requirements

- `nvme-cli` - NVMe command line tools
- `dd` - For verification
- `findmnt` or `mount` - For mount detection
- `lsof` - For process detection (optional)

## License

[License information]
