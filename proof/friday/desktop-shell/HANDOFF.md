# Handoffs — friday/desktop-shell → orchestrator

## Isolation (how I work)

The `friday/*` workers share one checkout + one HEAD in the main tree
(`/Users/adarshrajesh/AlphaWeek2/ankiCFA`). That is unsafe for parallel branch
work: a `git checkout`/commit by one worker moves the shared HEAD under another.
I now work in a dedicated linked worktree
(`/Users/adarshrajesh/AlphaWeek2/ankiCFA-desktop-shell`, branch
`friday/desktop-shell`), which **locks** my branch so no other worker can move
or reset it. I edit/build/test in the main tree (warm `out/`) and commit only in
the worktree, staging only desktop-shell-scoped files.

## Concurrency incident I cleaned up (FYI, no action needed)

While I committed increment 1, the `friday/ethics` worker had switched the shared
main-tree HEAD onto `friday/ethics`, so my branding commit (`d9687c72b`) landed
on **friday/ethics** and `friday/desktop-shell` got reset to `6ef32ec8c`.

Fix applied:
- Cherry-picked my clean commit onto `friday/desktop-shell` → `22013a473`, pushed.
- Reset `friday/ethics` back to its real tip `be05088ce` with `git reset --mixed`
  (drops only my stray commit; **all** working-tree files, incl. every worker's
  uncommitted WIP, left untouched). `friday/ethics` history is now exactly the
  ethics worker's own commits again.

No ethics files were changed. If the ethics worker sees my commit anywhere in
their history, it should be dropped — it belongs to desktop-shell.

## Requests to orchestrator

- None blocking. Scores are consumed via the Python `anki.cfa.*` API for now; when
  the `compute_cfa_scores` RPC lands, the mediasrv CFA-Home payload swaps to it
  with no shape change (same fields).
