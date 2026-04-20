#!/usr/bin/env bash
set -euo pipefail

CHANNEL="${1:-can0}"
BITRATE="${2:-1000000}"

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  echo "This script must be run as root." >&2
  echo "Example: sudo ./scripts/bringup_can.sh ${CHANNEL} ${BITRATE}" >&2
  exit 1
fi

if ! command -v ip >/dev/null 2>&1; then
  echo "Missing required command: ip" >&2
  exit 1
fi

if ! ip link show "$CHANNEL" >/dev/null 2>&1; then
  echo "CAN interface $CHANNEL does not exist." >&2
  echo "Check that your USB-CAN adapter is connected and recognized by the OS." >&2
  exit 1
fi

ip link set "$CHANNEL" down || true
ip link set "$CHANNEL" type can bitrate "$BITRATE"
ip link set "$CHANNEL" up

echo "Brought up $CHANNEL at bitrate $BITRATE."
ip -details link show "$CHANNEL"
