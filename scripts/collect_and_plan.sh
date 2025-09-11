#!/usr/bin/env bash
set -euo pipefail

# Collect and Plan Script - Phase 1 of simplified architecture
# Merges collect + format planning into single operation

# Source common utilities
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/nvme_utils.sh"

# Parse arguments
DEVICE=""
OUTPUT_DIR="build"

while [[ $# -gt 0 ]]; do
    case $1 in
        --device)
            DEVICE="$2"
            shift 2
            ;;
        --output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        /dev/nvme*)
            DEVICE="$1"
            shift
            ;;
        *)
            log_error "Unknown argument: $1"
            echo "Usage: $0 [--device <device>] [--output-dir <dir>]"
            exit 1
            ;;
    esac
done

# Set default device if none provided
if [ -z "$DEVICE" ]; then
    if command -v gum >/dev/null 2>&1; then
        DEVICE=$(gum choose --header "Choose NVMe device" $(ls /dev/nvme* 2>/dev/null | grep -E '^/dev/nvme[0-9]+$'))
        if [ -z "$DEVICE" ]; then
            log_error "No device selected"
            exit 1
        fi
    else
        DEVICE="/dev/nvme0"
        log_info "Using default device: $DEVICE"
    fi
fi

# Validate device
if ! validate_device "$DEVICE"; then
    exit 1
fi

# Get device paths
IFS='|' read -r CONTROLLER_DEVICE NAMESPACE_DEVICE <<< "$(get_device_paths "$DEVICE")"

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Generate timestamp
TS="$(date +%Y%m%d_%H%M%S)"
STATE_FILE="$OUTPUT_DIR/nvme_plan_${TS}.json"

log_info "Collecting device information and creating execution plan..."
log_info "Device: $DEVICE"
log_info "Controller: $CONTROLLER_DEVICE"
log_info "Namespace: $NAMESPACE_DEVICE"

# Extract comprehensive device information
DEVICE_INFO=$(extract_device_info "$CONTROLLER_DEVICE" "$NAMESPACE_DEVICE")
MODEL=$(echo "$DEVICE_INFO" | cut -d'|' -f1 | cut -d':' -f2)
SERIAL=$(echo "$DEVICE_INFO" | cut -d'|' -f2 | cut -d':' -f2)
FIRMWARE=$(echo "$DEVICE_INFO" | cut -d'|' -f3 | cut -d':' -f2)
CAPACITY_RAW=$(echo "$DEVICE_INFO" | cut -d'|' -f4 | cut -d':' -f2)
CAPACITY=$(convert_capacity "$CAPACITY_RAW")

# Get additional device capabilities
OACS=$(nvme id-ctrl "$CONTROLLER_DEVICE" | grep -E '^oacs\s*:' | head -1 | sed 's/.*:\s*//' | xargs || echo 'Unknown')
FNA=$(nvme id-ctrl "$CONTROLLER_DEVICE" | grep -E '^fna\s*:' | head -1 | sed 's/.*:\s*//' | xargs || echo 'Unknown')
ONCS=$(nvme id-ctrl "$CONTROLLER_DEVICE" | grep -E '^oncs\s*:' | head -1 | sed 's/.*:\s*//' | xargs || echo 'Unknown')
MDTS=$(nvme id-ctrl "$CONTROLLER_DEVICE" | grep -E '^mdts\s*:' | head -1 | sed 's/.*:\s*//' | xargs || echo 'Unknown')

# Get namespace information
NSZE=$(nvme id-ns "$NAMESPACE_DEVICE" -n 1 | grep -E '^nsze\s*:' | head -1 | sed 's/.*:\s*//' | xargs || echo 'Unknown')
NUSE=$(nvme id-ns "$NAMESPACE_DEVICE" -n 1 | grep -E '^nuse\s*:' | head -1 | sed 's/.*:\s*//' | xargs || echo 'Unknown')
NCAP=$(nvme id-ns "$NAMESPACE_DEVICE" -n 1 | grep -E '^ncap\s*:' | head -1 | sed 's/.*:\s*//' | xargs || echo 'Unknown')

# Get system information
HOSTNAME=$(hostname)
KERNEL_VERSION=$(uname -r)
SYSTEM_UUID=$(cat /etc/machine-id 2>/dev/null || echo 'Unknown')

# Determine recommended erase command based on capabilities
RECOMMENDED_CMD="nvme format $NAMESPACE_DEVICE -s 2 -n 1"
RECOMMENDED_METHOD="Crypto Erase (Recommended)"
ALTERNATIVE_CMD="nvme format $NAMESPACE_DEVICE -s 1 -n 1"
ALTERNATIVE_METHOD="User Data Erase"

# Create comprehensive execution plan
cat > "$STATE_FILE" << EOF
{
  "phase": "execution_plan",
  "timestamp": "$(date '+%Y/%m/%d %H:%M:%S')",
  "device_path": "$DEVICE",
  "controller_device": "$CONTROLLER_DEVICE",
  "namespace_device": "$NAMESPACE_DEVICE",
  "device_info": {
    "model": "$MODEL",
    "serial": "$SERIAL",
    "firmware": "$FIRMWARE",
    "capacity": "$CAPACITY",
    "capacity_raw": "$CAPACITY_RAW",
    "nsze": "$NSZE",
    "nuse": "$NUSE",
    "ncap": "$NCAP"
  },
  "capabilities": {
    "oacs": "$OACS",
    "fna": "$FNA",
    "oncs": "$ONCS",
    "mdts": "$MDTS"
  },
  "system_info": {
    "hostname": "$HOSTNAME",
    "kernel_version": "$KERNEL_VERSION",
    "system_uuid": "$SYSTEM_UUID"
  },
  "execution_plan": {
    "recommended_command": "$RECOMMENDED_CMD",
    "recommended_method": "$RECOMMENDED_METHOD",
    "alternative_command": "$ALTERNATIVE_CMD",
    "alternative_method": "$ALTERNATIVE_METHOD",
    "secure_erase_setting": 2,
    "namespace_id": 1,
    "estimated_duration": "Unknown",
    "risk_level": "DESTRUCTIVE"
  },
  "business_details": {
    "name": "${BUSINESS_NAME:-Not Applicable (BN)}",
    "address": "${BUSINESS_ADDRESS:-Not Applicable (BA)}",
    "contact_name": "${BUSINESS_CONTACT_NAME:-Not Applicable (BCN)}",
    "contact_phone": "${BUSINESS_CONTACT_PHONE:-Not Applicable (BCP)}",
    "email": "${BUSINESS_EMAIL:-}",
    "website": "${BUSINESS_WEBSITE:-}"
  },
  "technician_details": {
    "name": "${TECHNICIAN_NAME:-Not Provided}"
  }
}
EOF

log_info "Execution plan created: $STATE_FILE"
echo ""
echo "=================================================================================="
echo "EXECUTION PLAN SUMMARY"
echo "=================================================================================="
echo "Device: $DEVICE ($MODEL)"
echo "Serial: $SERIAL"
echo "Capacity: $CAPACITY"
echo "Firmware: $FIRMWARE"
echo ""
echo "RECOMMENDED COMMAND:"
echo "  $RECOMMENDED_CMD"
echo "  Method: $RECOMMENDED_METHOD"
echo ""
echo "ALTERNATIVE COMMAND:"
echo "  $ALTERNATIVE_CMD"
echo "  Method: $ALTERNATIVE_METHOD"
echo ""
echo "Next step: Run execute-and-report to perform the erase and generate reports"
echo "  mise run execute $STATE_FILE"
echo "=================================================================================="
