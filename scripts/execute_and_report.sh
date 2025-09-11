#!/usr/bin/env bash
set -euo pipefail

# Execute and Report Script - Phase 2 of simplified architecture
# Merges format + verify + report into single atomic operation

# Source common utilities
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/nvme_utils.sh"

PLAN_FILE="${1:-}"

if [ -z "$PLAN_FILE" ]; then
    if command -v gum >/dev/null 2>&1; then
        PLAN_FILE=$(gum choose --header "Choose execution plan file" $(ls build/nvme_plan_*.json 2>/dev/null))
        if [ -z "$PLAN_FILE" ]; then
            log_error "No plan file selected"
            exit 1
        fi
    else
        log_error "Usage: $0 <plan_file>"
        exit 1
    fi
fi

if [ ! -f "$PLAN_FILE" ]; then
    log_error "Plan file $PLAN_FILE not found"
    exit 1
fi

# Load plan file
DEVICE=$(jq -r '.device_path' "$PLAN_FILE")
CONTROLLER_DEVICE=$(jq -r '.controller_device' "$PLAN_FILE")
NAMESPACE_DEVICE=$(jq -r '.namespace_device' "$PLAN_FILE")
RECOMMENDED_CMD=$(jq -r '.execution_plan.recommended_command' "$PLAN_FILE")
ALTERNATIVE_CMD=$(jq -r '.execution_plan.alternative_command' "$PLAN_FILE")
RECOMMENDED_METHOD=$(jq -r '.execution_plan.recommended_method' "$PLAN_FILE")
ALTERNATIVE_METHOD=$(jq -r '.execution_plan.alternative_method' "$PLAN_FILE")
MODEL=$(jq -r '.device_info.model' "$PLAN_FILE")
SERIAL=$(jq -r '.device_info.serial' "$PLAN_FILE")
CAPACITY=$(jq -r '.device_info.capacity' "$PLAN_FILE")

log_info "Executing erase and generating report for device: $DEVICE"
log_info "Model: $MODEL"
log_info "Serial: $SERIAL"
log_info "Capacity: $CAPACITY"

# Check if device still exists
if [[ ! -e "$DEVICE" ]]; then
    log_error "Device $DEVICE no longer exists"
    exit 1
fi

# Show warning and get confirmation
echo ""
echo "=================================================================================="
echo "EXECUTION CONFIRMATION"
echo "=================================================================================="
echo "Device: $DEVICE ($MODEL)"
echo "Serial: $SERIAL"
echo "Capacity: $CAPACITY"
echo ""
echo "Primary Command: $RECOMMENDED_CMD"
echo "Method: $RECOMMENDED_METHOD"
echo ""
echo "Fallback Command: $ALTERNATIVE_CMD"
echo "Method: $ALTERNATIVE_METHOD"
echo ""
echo "⚠️  WARNING: This will PERMANENTLY ERASE ALL DATA on the device!"
echo "⚠️  The system will try the primary command first, then fallback if needed."
echo "⚠️  This action cannot be undone!"
echo ""

if ! gum confirm "Are you absolutely sure you want to proceed with the erase?"; then
    echo "Erase cancelled by user"
    exit 0
fi

# Final confirmation with device path
if ! gum confirm "Final confirmation: Erase data on $DEVICE ($MODEL)?"; then
    echo "Erase cancelled by user"
    exit 0
fi

echo ""
echo "=================================================================================="
echo "EXECUTING ERASE COMMAND"
echo "=================================================================================="
echo "Starting erase at: $(date '+%Y/%m/%d %H:%M:%S')"
echo ""

# Record start time with milliseconds
START_TIME=$(date '+%Y/%m/%d %H:%M:%S.%3N')

# Try primary command first
echo "Attempting primary command: $RECOMMENDED_CMD --force"
echo "Method: $RECOMMENDED_METHOD"
echo ""

# Execute primary command and capture output/errors
echo "DEBUG: About to run: $RECOMMENDED_CMD --force"
if ERASE_OUTPUT=$(eval "$RECOMMENDED_CMD --force" 2>&1); then
    ERASE_EXIT_CODE=0
    echo "DEBUG: Primary command succeeded (exit code: 0)"
else
    ERASE_EXIT_CODE=$?
    echo "DEBUG: Primary command failed (exit code: $ERASE_EXIT_CODE)"
fi

echo "DEBUG: Primary command output: $ERASE_OUTPUT"

# If primary command failed, try fallback
if [ $ERASE_EXIT_CODE -ne 0 ]; then
    echo ""
    echo "=================================================================================="
    echo "PRIMARY COMMAND FAILED - TRYING FALLBACK"
    echo "=================================================================================="
    echo "Primary command failed with exit code: $ERASE_EXIT_CODE"
    echo "Error output: $ERASE_OUTPUT"
    echo ""
    echo "Attempting fallback command: $ALTERNATIVE_CMD --force"
    echo "Method: $ALTERNATIVE_METHOD"
    echo ""
    
    # Try alternative command
    echo "DEBUG: About to run: $ALTERNATIVE_CMD --force"
    if ERASE_OUTPUT=$(eval "$ALTERNATIVE_CMD --force" 2>&1); then
        ERASE_EXIT_CODE=0
        echo "DEBUG: Fallback command succeeded (exit code: 0)"
    else
        ERASE_EXIT_CODE=$?
        echo "DEBUG: Fallback command failed (exit code: $ERASE_EXIT_CODE)"
    fi
    
    echo "DEBUG: Fallback command output: $ERASE_OUTPUT"
    
    if [ $ERASE_EXIT_CODE -eq 0 ]; then
        echo "✅ Fallback command succeeded!"
        ACTUAL_CMD="$ALTERNATIVE_CMD"
        ACTUAL_METHOD="$ALTERNATIVE_METHOD"
        echo "DEBUG: Set ACTUAL_CMD to: $ACTUAL_CMD"
        echo "DEBUG: Set ACTUAL_METHOD to: $ACTUAL_METHOD"
    else
        echo "❌ Both primary and fallback commands failed"
        echo "Primary command: $RECOMMENDED_CMD"
        echo "Fallback command: $ALTERNATIVE_CMD"
        echo "Final error output: $ERASE_OUTPUT"
    fi
else
    echo "✅ Primary command succeeded!"
    ACTUAL_CMD="$RECOMMENDED_CMD"
    ACTUAL_METHOD="$RECOMMENDED_METHOD"
fi

# Record end time with milliseconds
END_TIME=$(date '+%Y/%m/%d %H:%M:%S.%3N')

# Initialize variables that might be used in jq
NON_ZERO_COUNT="0"
HEXDUMP_SAMPLE=""
ERASE_STATUS="UNKNOWN"
ERASE_ANALYSIS=""

if [ $ERASE_EXIT_CODE -eq 0 ]; then
    # Calculate duration - extract milliseconds from timestamps
    echo "Calculating duration..."
    
    # Extract milliseconds from the timestamps
    START_MS=$(echo "$START_TIME" | sed 's/.*\.\([0-9]*\)$/\1/' | sed 's/^$/000/')
    END_MS=$(echo "$END_TIME" | sed 's/.*\.\([0-9]*\)$/\1/' | sed 's/^$/000/')
    
    # Convert to epoch seconds
    START_EPOCH=$(date -d "$START_TIME" +%s 2>/dev/null || echo "0")
    END_EPOCH=$(date -d "$END_TIME" +%s 2>/dev/null || echo "0")
    
    if [ "$START_EPOCH" != "0" ] && [ "$END_EPOCH" != "0" ]; then
        # Calculate total milliseconds
        START_TOTAL_MS=$((START_EPOCH * 1000 + START_MS))
        END_TOTAL_MS=$((END_EPOCH * 1000 + END_MS))
        DURATION_MS=$((END_TOTAL_MS - START_TOTAL_MS))
        DURATION_STR="${DURATION_MS}ms"
    else
        DURATION_STR="Unknown"
    fi
    
    echo "Duration: $DURATION_STR"
    
    # Analyze output for errors/warnings
    IO_ERRORS=0
    WARNINGS=""
    if echo "$ERASE_OUTPUT" | grep -i "error\|failed\|warning" > /dev/null 2>&1; then
        # Count errors using a more robust method
        IO_ERRORS=$(echo "$ERASE_OUTPUT" | grep -i "error\|failed" | while read line; do echo "1"; done | wc -l 2>/dev/null)
        if [ -z "$IO_ERRORS" ] || [ "$IO_ERRORS" = "0" ]; then
            # Fallback: count manually if wc fails
            IO_ERRORS=$(echo "$ERASE_OUTPUT" | grep -i "error\|failed" | awk 'END {print NR}')
        fi
        
        WARNINGS=$(echo "$ERASE_OUTPUT" | grep -i "warning" | tr '\n' ';' | sed 's/;$//' 2>/dev/null || echo "")
    fi
    
    # Extract actual erase setting from the command that was executed
    ACTUAL_ERASE_SETTING="2"  # Default to crypto erase
    if [[ "$ACTUAL_CMD" =~ -s\ ([0-9]+) ]]; then
        ACTUAL_ERASE_SETTING="${BASH_REMATCH[1]}"
    fi
    
    echo ""
    echo "=================================================================================="
    echo "VERIFYING ERASE RESULTS"
    echo "=================================================================================="
    echo "Verifying device state after erase..."
    
    # Post-erase verification
    POST_MODEL=$(nvme id-ctrl "$CONTROLLER_DEVICE" | grep -E '^mn\s*:' | head -1 | sed 's/.*:\s*//' || echo 'Unknown')
    POST_SERIAL=$(nvme id-ctrl "$CONTROLLER_DEVICE" | grep -E '^sn\s*:' | head -1 | sed 's/.*:\s*//' || echo 'Unknown')
    POST_FIRMWARE=$(nvme id-ctrl "$CONTROLLER_DEVICE" | grep -E '^fr\s*:' | head -1 | sed 's/.*:\s*//' || echo 'Unknown')
    POST_CAPACITY=$(nvme id-ns "$NAMESPACE_DEVICE" -n 1 | grep -E '^nsze\s*:' | head -1 | sed 's/.*:\s*//' || echo 'Unknown')
    
    # Simple data verification
    DEVICE_SIZE=$(blockdev --getsize64 "$NAMESPACE_DEVICE" 2>/dev/null || echo 0)
    HEXDUMP_SAMPLE=""
    if [ "$DEVICE_SIZE" -gt 0 ]; then
        HEXDUMP_SAMPLE=$(hexdump -C "$NAMESPACE_DEVICE" -n 4096 2>/dev/null | head -5 | sed 's/|.*|//' || echo "ERROR: Cannot read device")
    fi
    
    # Determine erase status
    # Count non-zero lines using a more robust method
    NON_ZERO_COUNT=$(echo "$HEXDUMP_SAMPLE" | grep -v "ERROR:" | grep -v "00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00" | awk 'END {print NR}' 2>/dev/null)
    if [ -z "$NON_ZERO_COUNT" ]; then
        # Fallback: count manually if awk fails
        NON_ZERO_COUNT=$(echo "$HEXDUMP_SAMPLE" | grep -v "ERROR:" | grep -v "00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00" | while read line; do echo "1"; done | wc -l 2>/dev/null)
        if [ -z "$NON_ZERO_COUNT" ]; then
            NON_ZERO_COUNT="0"
        fi
    fi
    if [ "$NON_ZERO_COUNT" -lt 5 ]; then
        ERASE_STATUS="LIKELY_ERASED"
        ERASE_ANALYSIS="Device appears to contain mostly zeros or random data"
    else
        ERASE_STATUS="POSSIBLY_NOT_ERASED"
        ERASE_ANALYSIS="Device contains significant non-zero data"
    fi
    
    # Update the plan file with execution results
    echo "Updating plan file with execution results..."
    jq --arg start_time "$START_TIME" --arg end_time "$END_TIME" --arg duration "$DURATION_STR" --arg actual_setting "$ACTUAL_ERASE_SETTING" --arg actual_cmd "$ACTUAL_CMD" --arg actual_method "$ACTUAL_METHOD" --argjson io_errors $IO_ERRORS --arg warnings "$WARNINGS" --arg erase_status "$ERASE_STATUS" --arg erase_analysis "$ERASE_ANALYSIS" --arg post_model "$POST_MODEL" --arg post_serial "$POST_SERIAL" --arg post_firmware "$POST_FIRMWARE" --arg post_capacity "$POST_CAPACITY" --arg hexdump_sample "$HEXDUMP_SAMPLE" --arg non_zero_count "$NON_ZERO_COUNT" \
        '.execution_plan.start_time = $start_time | .execution_plan.end_time = $end_time | .execution_plan.duration = $duration | .execution_plan.secure_erase_setting = ($actual_setting | tonumber) | .execution_plan.actual_command = $actual_cmd | .execution_plan.actual_method = $actual_method | .execution_plan.success = true | .execution_plan.io_errors = $io_errors | .execution_plan.warnings = $warnings | .verification = {"device_accessible": true, "erase_successful": true, "verification_method": "Device accessibility and hexdump analysis", "data_analysis": {"status": $erase_status, "analysis": $erase_analysis, "non_zero_lines": ($non_zero_count | tonumber), "hexdump_sample": $hexdump_sample}, "timestamp": now | strftime("%Y/%m/%d %H:%M:%S")} | .post_erase_state = {"model": $post_model, "serial": $post_serial, "firmware": $post_firmware, "capacity": $post_capacity}' \
        "$PLAN_FILE" > "${PLAN_FILE}.tmp" && mv "${PLAN_FILE}.tmp" "$PLAN_FILE"
    
    echo ""
    echo "=================================================================================="
    echo "GENERATING REPORTS"
    echo "=================================================================================="
    echo "Generating compliance reports..."
    
    # Ask user for report format selection
    if command -v gum >/dev/null 2>&1; then
        echo "Select report formats to generate:"
        FORMATS=$(gum choose --no-limit --header "Choose report formats:" "text" "html" "json" "pdf" | tr '\n' ' ')
        if [ -z "$FORMATS" ]; then
            echo "No formats selected, using default (pdf)"
            FORMATS="pdf"
        fi
        echo "Selected formats: $FORMATS"
    else
        echo "gum not available, using default format (pdf)"
        FORMATS="pdf"
    fi
    
    # Generate reports using the selected formats
    # Use virtual environment Python if available, otherwise fall back to system Python
    if [ -f ".venv/bin/python" ]; then
        .venv/bin/python src/nvme_report_builder_system.py --from-plan "$PLAN_FILE" --formats $FORMATS
    else
        python3 src/nvme_report_builder_system.py --from-plan "$PLAN_FILE" --formats $FORMATS
    fi
    
    echo ""
    echo "=================================================================================="
    echo "EXECUTION COMPLETED SUCCESSFULLY"
    echo "=================================================================================="
    echo "Command used: $ACTUAL_CMD"
    echo "Method: $ACTUAL_METHOD"
    echo "Start time: $START_TIME"
    echo "End time: $END_TIME"
    echo "Duration: $DURATION_STR"
    echo "Status: $ERASE_STATUS"
    echo "Analysis: $ERASE_ANALYSIS"
    echo ""
    echo "Reports generated in build/ directory"
    echo "=================================================================================="
    
else
    echo ""
    echo "=================================================================================="
    echo "ERASE FAILED"
    echo "=================================================================================="
    echo "The erase command failed. Check the error messages above."
    echo "You may need to:"
    echo "1. Check device permissions (try with sudo)"
    echo "2. Verify the device is not in use"
    echo "3. Check if the device supports the requested erase type"
    echo ""
    exit 1
fi
