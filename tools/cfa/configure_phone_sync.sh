#!/usr/bin/env bash
# CFA sync workstream — point AnkiDroid on the emulator at the self-hosted
# anki-sync-server and log it in, entirely from adb (PreferencesActivity is not
# exported, so we configure the SharedPreferences file directly via run-as).
#
#   tools/cfa/sync_server.py serve         # start the server first (mints hkey)
#   tools/cfa/configure_phone_sync.sh      # then run this
#
# Writes these AnkiDroid SharedPreferences keys (verified against the AnkiDroid
# source, com.ichi2.anki.Sync / settings/Prefs.kt / res/values/preferences.xml):
#   syncBaseUrl          custom sync server base URL  -> http://10.0.2.2:27701/
#   syncBaseUrl_switch   enable the custom server (bool)
#   hkey                 real login token minted by the server
#   username             account name (cfa)
# and clears currentSyncUri so getEndpoint() resolves to our custom URL.
set -uo pipefail

export ANDROID_SDK_ROOT="${ANDROID_SDK_ROOT:-/opt/homebrew/share/android-commandlinetools}"
export PATH="$ANDROID_SDK_ROOT/platform-tools:$ANDROID_SDK_ROOT/emulator:$PATH"

PKG="${CFA_PKG:-com.ichi2.anki.debug}"
DEV="${CFA_DEVICE:-emulator-5554}"
PREFS="shared_prefs/${PKG}_preferences.xml"
URL="${CFA_SYNC_URL:-http://10.0.2.2:27701/}"
USERNAME="${CFA_SYNC_USER:-cfa}"
INFO="${CFA_SYNC_INFO:-/tmp/cfa-syncserver/server-info.json}"
ADB_TIMEOUT="${CFA_ADB_TIMEOUT:-30}"

# adbq: run adb with a hard polling timeout so a hung adb never blocks us.
# adb output is sent to a temp file (not the $(...) pipe) because backgrounding
# adb inside a command substitution otherwise drops its stdout.
adbq() {
  local out; out="$(mktemp)"
  adb -s "$DEV" "$@" >"$out" 2>&1 &
  local pid=$! i=0
  while kill -0 "$pid" 2>/dev/null; do
    sleep 1; i=$((i + 1))
    if [ "$i" -ge "$ADB_TIMEOUT" ]; then kill -9 "$pid" 2>/dev/null; break; fi
  done
  wait "$pid" 2>/dev/null
  cat "$out"; rm -f "$out"
}

HKEY="${CFA_SYNC_HKEY:-$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["hkey"])' "$INFO")}"
if [ -z "$HKEY" ]; then echo "FATAL: no hkey (is the server up? $INFO)"; exit 1; fi
echo "[configure] device=$DEV url=$URL user=$USERNAME hkey=${HKEY:0:8}..."

echo "[configure] force-stopping $PKG so it won't overwrite prefs"
adbq shell am force-stop "$PKG"

echo "[configure] reading current prefs"
CUR="$(adbq exec-out run-as "$PKG" cat "$PREFS")"
if ! printf '%s' "$CUR" | grep -q '</map>'; then
  # prefs missing/empty (fresh install or a truncated file): start from a
  # minimal valid map, preserving the CFA bootstrap flag so the app does not
  # re-import the seed decks on next launch.
  echo "[configure] prefs empty/unreadable — using a minimal baseline map"
  CUR=$'<?xml version=\'1.0\' encoding=\'utf-8\' standalone=\'yes\' ?>\n<map>\n    <boolean name="cfa_bootstrap_imported" value="true" />\n</map>'
fi

NEW="$(URL="$URL" USERNAME="$USERNAME" HKEY="$HKEY" python3 - "$CUR" <<'PY'
import os, re, sys
cur = sys.argv[1]
url, username, hkey = os.environ["URL"], os.environ["USERNAME"], os.environ["HKEY"]
# drop any pre-existing sync-account keys so we write a clean state
for key in ("syncBaseUrl", "syncBaseUrl_switch", "hkey", "username", "currentSyncUri"):
    cur = re.sub(rf'\s*<(string|boolean) name="{re.escape(key)}"[^>]*(/>|>.*?</\1>)', "", cur)
inject = (
    f'    <string name="username">{username}</string>\n'
    f'    <string name="hkey">{hkey}</string>\n'
    f'    <string name="syncBaseUrl">{url}</string>\n'
    f'    <boolean name="syncBaseUrl_switch" value="true" />\n'
    "</map>"
)
assert "</map>" in cur, "prefs xml missing </map>"
sys.stdout.write(cur.replace("</map>", inject))
PY
)"
if ! printf '%s' "$NEW" | grep -q 'name="hkey"'; then echo "FATAL: prefs edit failed"; exit 1; fi

# Embed the base64 in the command (no stdin): adb exec-out does not deliver
# stdin EOF to a nested run-as/sh, so a piped `base64 -d` would hang forever.
echo "[configure] writing updated prefs back via run-as (embedded base64)"
B64="$(printf '%s' "$NEW" | base64 | tr -d '\n')"
adbq exec-out "run-as $PKG sh -c 'echo $B64 | base64 -d > $PREFS'"

echo "[configure] verifying on-device sync keys:"
adbq exec-out run-as "$PKG" cat "$PREFS" | grep -iE 'hkey|username|syncBaseUrl|currentSyncUri' || {
  echo "FATAL: sync keys not present after write"; exit 1; }

echo "[configure] launching AnkiDroid (DeckPicker)"
adbq exec-out am start -n "$PKG/com.ichi2.anki.IntentHandler" >/dev/null 2>&1
echo "[configure] done. AnkiDroid is now pointed at $URL as '$USERNAME'."
echo "[configure] Trigger a sync in the app (or tap Sync on the backup prompt)."
