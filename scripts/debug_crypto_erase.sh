#!/usr/bin/env bash
set -euo pipefail

echo "🔍 NVMe Crypto Erase Diagnostic Tool"
echo "===================================="
echo ""

# Get the first NVMe device if no argument provided
DEVICE="${1:-/dev/nvme0}"

if [[ ! -e "$DEVICE" ]]; then
    echo "❌ Device $DEVICE not found"
    echo "Available NVMe devices:"
    ls -la /dev/nvme* 2>/dev/null || echo "No NVMe devices found"
    exit 1
fi

echo "📱 Device: $DEVICE"
echo ""

# Get controller and namespace devices
CONTROLLER_DEVICE="$DEVICE"
NAMESPACE_DEVICE="${DEVICE}n1"

if [[ ! -e "$NAMESPACE_DEVICE" ]]; then
    echo "❌ Namespace device $NAMESPACE_DEVICE not found"
    echo "Available namespaces:"
    ls -la ${DEVICE}n* 2>/dev/null || echo "No namespaces found"
    exit 1
fi

echo "🎛️  Controller: $CONTROLLER_DEVICE"
echo "📦 Namespace: $NAMESPACE_DEVICE"
echo ""

# Get OACS value
echo "🔧 Checking OACS (Optional Admin Command Support)..."
OACS=$(nvme id-ctrl "$CONTROLLER_DEVICE" | grep -E '^oacs\s*:' | head -1 | sed 's/.*:\s*//' | xargs | sed 's/0x//')
echo "OACS: 0x$OACS"

# Decode OACS bits
echo ""
echo "📊 OACS Bit Analysis:"
if (( (0x$OACS & 0x01) )); then echo "Bit 0 (Security Send/Receive): ✅ Supported"; else echo "Bit 0 (Security Send/Receive): ❌ Not Supported"; fi
if (( (0x$OACS & 0x02) )); then echo "Bit 1 (Format NVM): ✅ Supported"; else echo "Bit 1 (Format NVM): ❌ Not Supported"; fi
if (( (0x$OACS & 0x04) )); then echo "Bit 2 (Firmware Commit/Download): ✅ Supported"; else echo "Bit 2 (Firmware Commit/Download): ❌ Not Supported"; fi
if (( (0x$OACS & 0x08) )); then echo "Bit 3 (Namespace Management): ✅ Supported"; else echo "Bit 3 (Namespace Management): ❌ Not Supported"; fi
if (( (0x$OACS & 0x10) )); then echo "Bit 4 (Device Self-test): ✅ Supported"; else echo "Bit 4 (Device Self-test): ❌ Not Supported"; fi
if (( (0x$OACS & 0x20) )); then echo "Bit 5 (Directives): ✅ Supported"; else echo "Bit 5 (Directives): ❌ Not Supported"; fi

echo ""
echo "🔐 Checking FNA (Format NVM Attributes)..."
FNA=$(nvme id-ctrl "$CONTROLLER_DEVICE" | grep -E '^fna\s*:' | head -1 | sed 's/.*:\s*//' | xargs | sed 's/0x//')
echo "FNA: 0x$FNA"

echo ""
echo "📊 FNA Bit Analysis:"
if (( (0x$FNA & 0x01) )); then echo "Bit 0 (Format All Namespaces): ✅ Supported"; else echo "Bit 0 (Format All Namespaces): ❌ Not Supported"; fi
if (( (0x$FNA & 0x02) )); then echo "Bit 1 (Secure Erase All Namespaces): ✅ Supported"; else echo "Bit 1 (Secure Erase All Namespaces): ❌ Not Supported"; fi
if (( (0x$FNA & 0x04) )); then echo "Bit 2 (Crypto Erase All Namespaces): ✅ Supported"; else echo "Bit 2 (Crypto Erase All Namespaces): ❌ Not Supported"; fi
if (( (0x$FNA & 0x08) )); then echo "Bit 3 (Format All Namespaces with Secure Erase): ✅ Supported"; else echo "Bit 3 (Format All Namespaces with Secure Erase): ❌ Not Supported"; fi
if (( (0x$FNA & 0x10) )); then echo "Bit 4 (Format All Namespaces with Crypto Erase): ✅ Supported"; else echo "Bit 4 (Format All Namespaces with Crypto Erase): ❌ Not Supported"; fi

echo ""
echo "🎯 Crypto Erase Support Analysis:"
if (( (0x$FNA & 0x04) )); then
    echo "✅ Crypto Erase (Bit 2) is SUPPORTED"
    echo "   Your drive should support: nvme format $NAMESPACE_DEVICE -s 2 -n 1"
else
    echo "❌ Crypto Erase (Bit 2) is NOT SUPPORTED"
    echo "   This is why -s2 (crypto erase) fails on your drive"
    echo "   You should use: nvme format $NAMESPACE_DEVICE -s 1 -n 1 (User Data Erase)"
fi

echo ""
echo "🛠️  Recommended Commands:"
if (( (0x$FNA & 0x04) )); then
    echo "1. Crypto Erase (Recommended): sudo nvme format $NAMESPACE_DEVICE -s 2 -n 1"
fi
if (( (0x$FNA & 0x02) )); then
    echo "2. User Data Erase (Fallback): sudo nvme format $NAMESPACE_DEVICE -s 1 -n 1"
fi

echo ""
echo "📋 Additional Device Info:"
MODEL=$(nvme id-ctrl "$CONTROLLER_DEVICE" | grep -E '^mn\s*:' | head -1 | sed 's/.*:\s*//' | xargs)
SERIAL=$(nvme id-ctrl "$CONTROLLER_DEVICE" | grep -E '^sn\s*:' | head -1 | sed 's/.*:\s*//' | xargs)
FIRMWARE=$(nvme id-ctrl "$CONTROLLER_DEVICE" | grep -E '^fr\s*:' | head -1 | sed 's/.*:\s*//' | xargs)

echo "Model: $MODEL"
echo "Serial: $SERIAL"
echo "Firmware: $FIRMWARE"

echo ""
echo "🔍 Raw OACS and FNA values for reference:"
echo "OACS (hex): 0x$OACS"
echo "FNA (hex): 0x$FNA"
echo "OACS (binary): $(echo "obase=2; ibase=16; $OACS" | bc)"
echo "FNA (binary): $(echo "obase=2; ibase=16; $FNA" | bc)"
