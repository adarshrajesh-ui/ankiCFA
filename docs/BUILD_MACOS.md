# BUILD (fork) — Reproducible macOS build + run

> Fork deliverable "BUILD.md". Named `BUILD_MACOS.md` because macOS's
> case-insensitive filesystem makes `docs/BUILD.md` collide with the existing
> `docs/build.md` (upstream's "build system" doc, unrelated).

Fork of [ankitects/anki](https://github.com/ankitects/anki), AGPL-3.0-or-later.
This documents the exact steps used to build the fork from source and launch it
on macOS (Apple Silicon), plus how to verify the build.

## Verified environment

- **Commit:** `7f591d85e67e7b29dc287afb3ec743d68fa8f501` (branch
  `gnhf/context-discipline-i-ef2200`)
- **OS:** macOS 15.6.1 (build 24G90), `Darwin arm64` (Apple Silicon)
- **Rust:** 1.92.0 (pinned by `rust-toolchain.toml`; auto-installed by rustup)
- **just:** 1.55.1 (installed via Homebrew)
- **Python:** the build downloads and manages its own Python via `uv`
  (`out/pyenv`, Python 3.13). No system Python is required for the build.
- Node, protoc, uv are downloaded automatically into `out/` by the build system.

## Prerequisites (install once)

```bash
# 1. Rust toolchain manager (rustup). The pinned 1.92.0 toolchain in
#    rust-toolchain.toml is fetched automatically on first build.
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# 2. just command runner (official task runner for this repo)
brew install just

# 3. Git submodules (only needed to run the qt installer test suite). These are
#    the Briefcase app templates; without them qt/tests/test_installer.py fails
#    with "Unable to clone application template".
git submodule update --init qt/installer/mac-template qt/installer/windows-template
```

The build system itself downloads N2/Ninja, Node, protoc and uv on demand, so no
other manual toolchain installation is needed on macOS. The submodule step above
is not needed to build or launch the app — only to run the installer tests that
`just test` (and `scripts/verify_desktop.sh`) exercise.

## Build

From the repository root:

```bash
just build          # builds pylib + qt (debug); == `./ninja pylib qt`
```

The first build downloads and compiles all dependencies and takes several
minutes (~1–2 min of Rust compilation once deps are cached; longer cold). A
successful run ends with `Build succeeded in <N>s.`

For a release-optimized build: `just run-optimized`, or `RELEASE=1 just build`.

## Run (launch the desktop app)

```bash
just run            # builds if needed, then launches Anki with ANKIDEV enabled
```

Web views are served at http://localhost:40000/_anki/pages/ during development.

## Verify the build without launching a GUI

The built Python package imports and loads the compiled Rust backend:

```bash
PYTHONPATH="out/pylib:out/qt" out/pyenv/bin/python -c \
  "import anki, anki.collection; from anki._backend import RustBackend; \
   from anki.buildinfo import version; print('anki', version, 'RustBackend OK')"
# -> anki 26.05 RustBackend OK
```

Built artifacts of note:

- `out/pylib/anki/_rsbridge.so` — compiled Rust backend (PyO3 extension)
- `out/pylib/anki/*_pb2.py` — generated protobuf Python bindings
- `out/qt/_aqt/` — built Qt GUI package
- `out/pyenv/bin/python` — managed Python interpreter

## One-shot verification script

`scripts/verify_desktop.sh` builds from source, runs the full existing test
suite plus this fork's added Rust + Python tests, and asserts the built app
exists. It exits 0 only if everything passes and prints a PASS/FAIL summary.

```bash
bash scripts/verify_desktop.sh
```

## Notes / gotchas

- Do **not** invoke `./ninja`, `./run`, or `tools/*` directly — use the `just`
  recipes (`just --list` for the full set). They wrap the build system in `build/`.
- The repo path must not contain spaces.
- macOS filesystem is case-insensitive: avoid creating `docs/BUILD.md`, it
  aliases the existing `docs/build.md`.
- `out/` is fully generated; delete it for a clean build.
- Cargo/uv/node caches live in `~/.cargo`, `~/.rustup`, `~/.cache` and are shared
  across builds.
