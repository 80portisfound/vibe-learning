# Hermes Vibe Desktop

Hermes Vibe Desktop is an Electron + React workbench for running Hermes Agent backed coding sessions with a live learning/debugging dashboard. The app starts a bundled FastAPI backend, uses the local Hermes home at `~/.hermes` by default, and packages the vendored Hermes fork metadata with the desktop build.

## Current Release

- Version: `0.1.0`
- Platform built locally: macOS arm64
- App bundle: `apps/desktop/release/mac-arm64/Hermes Vibe.app`
- DMG: `apps/desktop/release/Hermes-Vibe-0.1.0-arm64.dmg`
- ZIP: `apps/desktop/release/Hermes-Vibe-0.1.0-arm64.zip`

## What Is Included

- Agent create/edit/archive/delete/restore flows
- Session create/edit/archive/delete/restore and duplicate cleanup
- Hermes Home path management with backend repoint/restart
- Memory and skills file editors with snapshots before writes
- Honcho status panel
- Model selection and per-message Hermes model override plumbing
- Streaming chat panel with cancel support
- Dashboard cards for learning concepts, implementation status, tracking summaries, and debugging signals
- Packaged Python runtime for the FastAPI backend
- Hermes fork metadata endpoint at `/hermes/fork`

## Known Limits

- macOS artifacts are ad-hoc signed only when no Apple Developer ID certificate is available.
- Notarization is skipped until Apple Developer credentials are configured.
- The vendored Hermes metadata points to upstream commit `75e1339d4cdb32652e560eccc3930cc9264ac67b`.
- The backend Hermes runtime adapter still has a local integration note that deeper adapter work remains.
- The packaged runtime is macOS arm64 because it is built from the local machine Python.

## Install And Run

From the repository root, open:

```bash
open "apps/desktop/release/mac-arm64/Hermes Vibe.app"
```

If macOS blocks the app because it is not notarized, use Finder's Open flow or the Security & Privacy prompt for local testing. Production distribution should use a notarized build.

The app starts its own backend. By default that backend uses:

```text
HERMES_HOME=~/.hermes
```

Inside the app, use the Hermes Home settings panel to point at a different Hermes home and restart the backend.

## Development

Install desktop dependencies:

```bash
cd apps/desktop
npm install
```

Run the frontend dev server:

```bash
npm run dev
```

Run the Electron shell against built Electron sources:

```bash
npm run desktop
```

Run backend tests:

```bash
cd apps/api
/private/tmp/hermes-vibe-api-venv/bin/pytest -q
```

Run Electron tests:

```bash
cd apps/desktop
npm run test:electron
```

## Packaging

Build the app directory:

```bash
cd apps/desktop
npm run package:dir
```

Build the macOS DMG and ZIP:

```bash
cd apps/desktop
npm run package:mac
```

Packaging performs:

1. Icon generation
2. React/Vite production build
3. Electron TypeScript build
4. Python runtime creation from `apps/api/requirements-runtime.txt`
5. Electron Builder packaging

The Python runtime intentionally installs runtime-only API requirements. Test tooling such as `pytest` and `httpx` stays in `apps/api/requirements-dev.txt`.

## Verification Checklist

Before calling a build distributable, run:

```bash
cd apps/desktop
npm audit --omit=dev
npm audit
npm run test:electron
npm run build
npm run package:dir
```

Then return to the repository root and smoke test the packaged backend:

```bash
cd ../..
HERMES_VIBE_API_PORT=8110 "./apps/desktop/release/mac-arm64/Hermes Vibe.app/Contents/MacOS/Hermes Vibe"
curl -fsS http://127.0.0.1:8110/health
curl -fsS http://127.0.0.1:8110/hermes/fork
```

Stop the smoke-test app with `Ctrl-C`.

## Release Signing

For production macOS distribution, configure Electron Builder with:

- Apple Developer ID Application certificate
- Apple ID or App Store Connect API credentials for notarization
- Hardened runtime and entitlements as needed for the final app surface

After credentials are configured, rerun:

```bash
cd apps/desktop
npm run package:mac
```

The current unsigned local build is suitable for internal development and QA, not polished public distribution.
