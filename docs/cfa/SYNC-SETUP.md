# CFA Sync Setup — real desktop ⇄ phone round-trip

Phase-0 harness for a **real** two-way sync between desktop ankiCFA and the
AnkiDroid client, using a self-hosted Anki sync server on the LAN. This is what
acceptance items **D4** (two-way round-trip) and **D5** (offline-then-sync) are
demonstrated against.

## 1. Start the server (host machine)

```
just cfa-syncserver
```

It stands up a long-running `anki-sync-server` (the Rust one, built into the
backend) with **fixed credentials** so every device uses the same values, binds
to all interfaces, and prints the URLs to use. Ctrl-C stops it; data persists in
`~/.cfa-syncserver` across restarts.

| setting   | default             | env override    |
| --------- | ------------------- | --------------- |
| username  | `cfa`               | `CFA_SYNC_USER` |
| password  | `cfa-exam-2026`     | `CFA_SYNC_PASS` |
| port      | `27701`             | `CFA_SYNC_PORT` |
| host/bind | `0.0.0.0` (LAN)     | `CFA_SYNC_HOST` |
| data dir  | `~/.cfa-syncserver` | `CFA_SYNC_BASE` |

The password is printed only to the local console, never to a network log, and
is never committed.

The recipe prints the three URLs it computed:

- **desktop, same machine:** `http://127.0.0.1:27701/`
- **desktop on another box / real phone:** `http://<host-LAN-IP>:27701/`
- **Android emulator:** `http://10.0.2.2:27701/` (the emulator's alias for the
  host loopback — this is the key gotcha; `localhost` inside the emulator is the
  emulator itself, not your machine).

## 2. Point the desktop at it

Preferences ▸ **Syncing** ▸ enable a self-hosted sync server and set the URL to
the desktop URL above. Log in once with `cfa` / `cfa-exam-2026`. First sync from
the device that already has the CFA deck uploads it; the other device downloads.

## 3. Point AnkiDroid at it

Settings ▸ **Sync** ▸ **Custom sync server** ▸ set both the sync URL and media
URL to the emulator/real-phone URL above, then log in with the same credentials.

- **Emulator:** use `http://10.0.2.2:27701/`.
- **Real phone on the same Wi-Fi:** use `http://<host-LAN-IP>:27701/` (the
  server must be reachable — same network, host firewall allows the port).

## 4. Prove the round-trip (D4 / D5)

1. Review a few CFA cards on the **emulator**, then Sync.
2. Sync on the **desktop** → the emulator's reviews appear (revlog + scores move).
3. Review different cards on the **desktop**, Sync, then Sync the emulator →
   they appear there. Reverse direction confirmed.
4. **Offline-then-sync (D5):** turn off the emulator's network, review, then
   re-enable and Sync — the queued reviews reconcile.

Because the honest scores now come from the shared `ComputeCfaScores` engine and
graded reviews are **de-duplicated per (card, day)** (see
[NATIVE-CFA-SPEC.md](NATIVE-CFA-SPEC.md)), reviewing the _same_ card offline on
both devices before syncing does **not** double-count — the scores stay honest
after the round-trip. Record the screen captures for D4 under `proof/friday/`.

## CI variant

`tools/cfa/sync_roundtrip.py` (recipe `just cfa-sync`) drives the same server
programmatically in a throwaway temp dir for an automated, self-contained
round-trip — use it in tests; use `just cfa-syncserver` for the live demo.
