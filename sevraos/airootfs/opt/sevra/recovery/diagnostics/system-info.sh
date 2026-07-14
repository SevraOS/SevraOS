#!/bin/bash

echo "=== Sevra Recovery Diagnostics ==="
echo

echo "[Kernel]"
uname -a

echo
echo "[Memory]"
free -h

echo
echo "[Disk]"
df -h

echo
echo "Diagnostics Complete"