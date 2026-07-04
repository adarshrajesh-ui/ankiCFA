#!/usr/bin/env bash
# CFA sync workstream — reliably trigger an AnkiDroid sync on the emulator and
# report the outcome from logcat.
#
# The CFA AnkiDroid build auto-navigates to custom activities (Exam
# Priority/Readiness/Config), which makes tapping the DeckPicker sync icon at a
# fixed pixel flaky. This script:
#   1. cold-launches (force-stop + IntentHandler) and waits for a stable DeckPicker
#      (a committed review survives force-stop, so nothing is lost),
#   2. locates the Sync button dynamically via `uiautomator dump` (content-desc),
#   3. taps it and reads the sync result from logcat,
#   4. optionally resolves the full-sync "Select collection to keep" dialog.
#
#   tools/cfa/phone_sync.sh              # normal sync
#   tools/cfa/phone_sync.sh phone        # if a full-sync dialog appears, keep the phone (upload)
#   tools/cfa/phone_sync.sh server       # ...keep the server (download)
set -uo pipefail
export ANDROID_SDK_ROOT="${ANDROID_SDK_ROOT:-/opt/homebrew/share/android-commandlinetools}"
export PATH="$ANDROID_SDK_ROOT/platform-tools:$ANDROID_SDK_ROOT/emulator:$PATH"

PKG="${CFA_PKG:-com.ichi2.anki.debug}"
DEV="${CFA_DEVICE:-emulator-5554}"
KEEP="${1:-}"

a() { adb -s "$DEV" exec-out "$@"; }

# ui_center <grep-regex> : echo "cx cy" of the first matching node's bounds.
ui_center() {
  a uiautomator dump /sdcard/ui.xml >/dev/null 2>&1
  a cat /sdcard/ui.xml 2>/dev/null | tr '<' '\n<' | grep -E "$1" \
    | grep -oE 'bounds="\[[0-9]+,[0-9]+\]\[[0-9]+,[0-9]+\]"' | head -1 \
    | grep -oE '[0-9]+' | {
      read -r x1; read -r y1; read -r x2; read -r y2
      [ -n "${y2:-}" ] && echo "$(((x1 + x2) / 2)) $(((y1 + y2) / 2))"
    }
}

echo "[phone_sync] cold-launch to a stable DeckPicker"
a am force-stop "$PKG" >/dev/null 2>&1
sleep 2
a am start -n "$PKG/com.ichi2.anki.IntentHandler" >/dev/null 2>&1
for _ in $(seq 1 20); do
  act="$(a dumpsys activity activities 2>/dev/null | grep -m1 ResumedActivity)"
  echo "$act" | grep -q "DeckPicker" && break
  sleep 1
done
sleep 2
act="$(a dumpsys activity activities 2>/dev/null | grep -m1 ResumedActivity)"
if ! echo "$act" | grep -q "DeckPicker"; then
  echo "WARN: not on DeckPicker: $act"
fi

echo "[phone_sync] locating Sync button"
read -r cx cy < <(ui_center 'content-desc="Sync"')
if [ -z "${cx:-}" ]; then
  echo "FATAL: Sync button not found"; a screencap -p > /tmp/phone_sync_fail.png; exit 1
fi
echo "[phone_sync] tap Sync at ($cx,$cy)"
a logcat -c >/dev/null 2>&1
a input tap "$cx" "$cy"
sleep 6

# Resolve a full-sync "Select collection to keep" dialog if requested/needed.
want=""
[ "$KEEP" = "phone" ] && want='text="AnkiDroid"'
[ "$KEEP" = "server" ] && want='text="AnkiWeb"'
if [ -n "$want" ]; then
  read -r bx by < <(ui_center "$want")
  if [ -n "${bx:-}" ]; then
    echo "[phone_sync] full-sync dialog present -> keep $KEEP"
    a input tap "$bx" "$by"; sleep 3
    read -r rx ry < <(ui_center 'text="Replace"')
    if [ -n "${rx:-}" ]; then a input tap "$rx" "$ry"; sleep 8; fi
  fi
fi
sleep 4

echo "[phone_sync] outcome:"
a logcat -d 2>/dev/null | grep -iE "SyncKt|sync result|Full (Upload|Download)|Normal sync complete|snackbar|sanity" | tail -10
