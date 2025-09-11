#!/usr/bin/env bash
# Common utilities for NVMe scripts

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Device validation
validate_device() {
    local device="$1"
    
    if [[ ! "$device" =~ ^/dev/nvme[0-9]+(n[0-9]+)?$ ]]; then
        log_error "Device path must be in format /dev/nvme0, /dev/nvme1, /dev/nvme0n1, etc."
        return 1
    fi
    
    if [[ ! -e "$device" ]]; then
        log_error "Device $device does not exist"
        return 1
    fi
    
    if ! nvme id-ctrl "$device" >/dev/null 2>&1; then
        log_error "Cannot access device $device with nvme commands"
        return 1
    fi
    
    return 0
}

# Get device paths
get_device_paths() {
    local device="$1"
    local controller_device="$device"
    local namespace_device="$device"
    
    # If we have a controller device, try to find the first namespace
    if [[ "$device" =~ ^/dev/nvme[0-9]+$ ]]; then
        namespace_device="${device}n1"
        if [[ ! -e "$namespace_device" ]]; then
            # Try to find the first namespace device
            FIRST_NS=$(nvme list | grep "$device" | head -1 | awk '{print $1}' | grep -o 'n[0-9]\+' | head -1)
            if [[ -n "$FIRST_NS" ]]; then
                namespace_device="${device}${FIRST_NS}"
            else
                log_warn "No namespace found for $device"
                namespace_device=""
            fi
        fi
    fi
    
    echo "$controller_device|$namespace_device"
}

# Extract device info
extract_device_info() {
    local controller_device="$1"
    local namespace_device="$2"
    
    local model=$(nvme id-ctrl "$controller_device" | grep -E '^mn\s*:' | head -1 | sed 's/.*:\s*//' | xargs || echo 'Unknown')
    local serial=$(nvme id-ctrl "$controller_device" | grep -E '^sn\s*:' | head -1 | sed 's/.*:\s*//' | xargs || echo 'Unknown')
    local firmware=$(nvme id-ctrl "$controller_device" | grep -E '^fr\s*:' | head -1 | sed 's/.*:\s*//' | xargs || echo 'Unknown')
    local capacity=$(nvme id-ns "$namespace_device" -n 1 | grep -E '^nsze\s*:' | head -1 | sed 's/.*:\s*//' | xargs || echo 'Unknown')
    
    echo "model:$model|serial:$serial|firmware:$firmware|capacity:$capacity"
}

# Convert capacity to human readable
convert_capacity() {
    local nsze_hex="$1"
    if [ -z "$nsze_hex" ] || [ "$nsze_hex" = "Unknown" ]; then
        echo "Unknown"
        return
    fi
    
    # Remove 0x prefix if present
    nsze_hex="${nsze_hex#0x}"
    
    # Convert hex to decimal
    local nsze_decimal=$((0x$nsze_hex))
    
    # Convert to GB (assuming 512-byte logical blocks)
    local capacity_gb=$((nsze_decimal * 512 / 1024 / 1024 / 1024))
    
    if [ $capacity_gb -gt 1024 ]; then
        local capacity_tb=$((capacity_gb / 1024))
        echo "${capacity_tb}TB"
    else
        echo "${capacity_gb}GB"
    fi
}

# Create JSON state file
create_state_file() {
    local device="$1"
    local controller_device="$2"
    local namespace_device="$3"
    local output_file="$4"
    local state_file="$5"
    
    # Extract device info
    local device_info=$(extract_device_info "$controller_device" "$namespace_device")
    local model=$(echo "$device_info" | cut -d'|' -f1 | cut -d':' -f2)
    local serial=$(echo "$device_info" | cut -d'|' -f2 | cut -d':' -f2)
    local firmware=$(echo "$device_info" | cut -d'|' -f3 | cut -d':' -f2)
    local capacity_raw=$(echo "$device_info" | cut -d'|' -f4 | cut -d':' -f2)
    local capacity=$(convert_capacity "$capacity_raw")
    
    # Get capabilities
    local oacs=$(nvme id-ctrl "$controller_device" | grep -E '^oacs\s*:' | head -1 | sed 's/.*:\s*//' | xargs || echo 'Unknown')
    local fna=$(nvme id-ctrl "$controller_device" | grep -E '^fna\s*:' | head -1 | sed 's/.*:\s*//' | xargs || echo 'Unknown')
    
    # Determine recommended command
    local recommended_cmd="nvme format $namespace_device -s 2 -n 1"
    
    # Create JSON
    cat > "$state_file" << EOF
{
  "phase": "pre_erase",
  "timestamp": "$(date '+%Y/%m/%d %H:%M:%S')",
  "device_path": "$device",
  "controller_device": "$controller_device",
  "namespace_device": "$namespace_device",
  "output_file": "$output_file",
  "planned_erase": {
    "secure_erase_setting": 2,
    "namespace_id": 1,
    "command": "$recommended_cmd"
  },
  "pre_erase_state": {
    "model": "$model",
    "serial": "$serial",
    "firmware": "$firmware",
    "capacity": "$capacity",
    "oacs": "$oacs",
    "fna": "$fna"
  }
}
EOF
}

# Show recommended commands
show_recommendations() {
    local device="$1"
    local controller_device="$2"
    local namespace_device="$3"
    
    log_info "RECOMMENDED ERASE COMMANDS:"
    echo "1. Check current format:"
    echo "   nvme id-ns $namespace_device -n 1"
    echo ""
    echo "2. RECOMMENDED Command:"
    echo "   sudo nvme format $namespace_device -s 2 -n 1"
    echo ""
    echo "3. Alternative Commands:"
    echo "   sudo nvme format $controller_device -s 2"
    echo "   sudo nvme format $namespace_device -s 1 -n 1"
    echo ""
    log_warn "WARNING: These commands are DESTRUCTIVE and will permanently erase all data!"
}
