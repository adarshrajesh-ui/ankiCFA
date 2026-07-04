# friday/sync — real two-way phone↔desktop sync (evidence log)

Workstream: **W-sync** (branch `friday/sync`). Goal: prove real two-way
phone↔desktop sync on the self-hosted `anki-sync-server` — no lost / double-
counted reviews, offline-then-sync, cross-device ethics attempt detail.

Fixed sync facts (see `tools/cfa/sync_server.py`):
`user=cfa  pass=cfa-friday  port=27701  base=/tmp/cfa-syncserver`
desktop endpoint `http://127.0.0.1:27701/`, phone endpoint `http://10.0.2.2:27701/`.

Test/build reuse (no cold Rust build — Python/scripts/config only):
```
PYTHONPATH="$PWD/pylib:/Users/adarshrajesh/AlphaWeek2/ankiCFA/out/pylib:." \
  /Users/adarshrajesh/AlphaWeek2/ankiCFA/out/pyenv/bin/python -m pytest pylib/tests/<file> -q
```
`anki` resolves as a namespace-package merge: worktree `pylib/anki/*.py` (edits win)
+ main tree `out/pylib/anki` (compiled `_rsbridge.so` + generated modules).

---

## Increment 1 — stand up the server; point + log in desktop AND phone ✅

**Server:** `tools/cfa/sync_server.py serve` → UP on `0.0.0.0:27701`, minted a real
login hkey `4bc75c95…`. Info: `/tmp/cfa-syncserver/server-info.json`.

**Phone (AnkiDroid on emulator-5554, `com.ichi2.anki.debug`):**
`PreferencesActivity` is not exported, so configured via `run-as` SharedPreferences
write (`tools/cfa/configure_phone_sync.sh`): `syncBaseUrl=http://10.0.2.2:27701/`,
`syncBaseUrl_switch=true`, `hkey`, `username=cfa`. Then triggered a real sync in the
app. Logcat proves the phone reached the host and uploaded:
`Sync: Normal collection sync` → `fetching meta…` → `sync result: FULL_UPLOAD` →
`Full Upload Completed` → snackbar `'Full sync from local'`. This **confirms
emulator→10.0.2.2:27701 reachability + hkey auth** (the previously-open question).

**Desktop (real `Collection` via `tools/cfa/desktop_sync.py sync`):** pointed at
`http://127.0.0.1:27701/`, logged in as cfa, `FULL_DOWNLOAD` → pulled the phone's
collection (**660 cards / 660 notes / 3 revlog**, decks CFA, CFA Level II,
CFA::Ethics Passages, y). Both devices now share one collection via the server.

BEFORE evidence:
- `proof/friday/sync/inc1-before-00-deckpicker.png` — emulator DeckPicker (pre-config)
- `proof/friday/sync/inc1-before-prefs.txt`, `inc1-before-prefs-fresh.txt` — on-device
  prefs showing NO hkey / username / syncBaseUrl (not logged in, no custom server)

AFTER evidence:
- `proof/friday/sync/inc1-after-02-ankidroid.png` — app up with backup/Sync prompt
- `proof/friday/sync/inc1-after-04-syncing.png` — DeckPicker synced (sync badge cleared)
- `proof/friday/sync/inc1-after-05-sync-settings.png` — **Sync settings: AnkiWeb
  account = cfa AND Custom sync server = http://10.0.2.2:27701/** (logged-in + URL)
- `proof/friday/sync/inc1-nav-drawer.png`, `inc1-settings.png` — navigation trail
- `proof/friday/sync/inc1-after-sync-logcat.txt` — the FULL_UPLOAD sync log
- `proof/friday/sync/inc1-after-desktop-sync.txt` — desktop FULL_DOWNLOAD summary

Scope files: `tools/cfa/sync_server.py`, `tools/cfa/adb_helpers.sh`,
`tools/cfa/configure_phone_sync.sh`, `tools/cfa/desktop_sync.py`,
justfile recipes `cfa-syncserver` / `cfa-sync-dedup-test`.

Commit: <inc1-sha>   PR: <pr-link>
