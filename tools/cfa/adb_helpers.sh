# CFA sync workstream — adb helpers (source this).
# adb is NOT on PATH and can hang; every call here is timeout-guarded.
#
#   source tools/cfa/adb_helpers.sh
#   adbq devices -l                 # timeout-guarded adb
#   adbcap proof/friday/sync/x.png  # screenshot -> local path
#   adbprefs                        # dump AnkiDroid shared prefs
#
# Fixed sync facts for the CFA self-hosted server (increment 1):
#   host-reachable-from-phone: http://10.0.2.2:27701/
#   user: cfa   pass: cfa-friday   port: 27701
export ANDROID_SDK_ROOT="${ANDROID_SDK_ROOT:-/opt/homebrew/share/android-commandlinetools}"
export PATH="$ANDROID_SDK_ROOT/platform-tools:$ANDROID_SDK_ROOT/emulator:$PATH"

CFA_PKG="com.ichi2.anki.debug"
CFA_ADB_TIMEOUT="${CFA_ADB_TIMEOUT:-20}"

# adbq <args...> : run adb with a hard timeout so a hung adb never blocks us.
adbq() {
  local t="$CFA_ADB_TIMEOUT"
  ( adb "$@" ) & local p=$!
  ( sleep "$t"; kill -9 "$p" 2>/dev/null ) & local w=$!
  wait "$p" 2>/dev/null; local rc=$?
  kill "$w" 2>/dev/null; wait "$w" 2>/dev/null
  return $rc
}

# adbcap <local.png> : reliable screenshot via on-device file + pull.
adbcap() {
  local out="$1"
  adbq shell screencap -p /sdcard/_cfacap.png >/dev/null 2>&1
  adbq pull /sdcard/_cfacap.png "$out" >/dev/null 2>&1
  adbq shell rm -f /sdcard/_cfacap.png >/dev/null 2>&1
  if [ -s "$out" ]; then echo "captured $out ($(wc -c < "$out") bytes)"; else echo "CAPTURE FAILED $out"; return 1; fi
}

# adbprefs : print AnkiDroid's main shared-prefs xml.
adbprefs() {
  adbq shell run-as "$CFA_PKG" cat "shared_prefs/${CFA_PKG}_preferences.xml"
}

# adbtap <x> <y>
adbtap() { adbq shell input tap "$1" "$2"; }
# adbtext "str"  (spaces must be %s or use adbq directly)
adbtext() { adbq shell input text "$1"; }
