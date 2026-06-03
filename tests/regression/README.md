# tap-quickbooks — Python 3.11 Regression Tests

Before/after parity test for the Python 3.9 → 3.11 migration.

## Strategy

1. **Capture** baseline on pre-migration `master` + Python 3.9: discover, select target streams, sync, record schemas / state-key names / record field names.
2. **Compare** on migration branch + Python 3.11 — assert schemas unchanged, no streams dropped, all baseline fields still present.

## Files

| File | Purpose |
| --- | --- |
| `conftest.py` | Shared fixtures: config builder, discover + select, sync runner, message parser |
| `capture.py` | Standalone — run once on Python 3.9 to write `baseline/` |
| `test_regression.py` | pytest suite — run on Python 3.11 to verify parity |
| `run_capture.sh` | Wrapper that runs `capture.py` in `python:3.9-slim` Docker |
| `run_tests.sh` | Wrapper that runs pytest in `python:3.11-slim` Docker |
| `baseline/` | Committed reference output: schemas, state keys, record fields, meta |

By default only the `accounts` stream is selected. Override via
`TAP_QUICKBOOKS_INCLUDE_STREAMS="accounts,customers,..."`.

## Why dev_mode and why is it not in the source

QuickBooks rotates the refresh_token on **every** call to Intuit's
`/oauth2/v1/tokens/bearer` endpoint. If the regression harness used the
standard refresh flow, every test run would consume a token off the same
lineage prod's scheduler also uses — racing prod and possibly causing its
next sync to `invalid_grant`.

The tap already has a `dev_mode` branch in
`tap_quickbooks/client.py:147-166` that bypasses the refresh endpoint
entirely and uses a pre-issued `access_token`. The branch is currently
CLI-gated via `--dev`, which Peliqan's fork of singer-python doesn't expose
(see commented-out block in `tap_quickbooks/__init__.py`).

**To run the regression, you must apply the patch below locally — it is
deliberately NOT committed**, because the production code path should keep
running the standard refresh flow.

### Patch to apply before testing (revert after)

In `tap_quickbooks/__init__.py`, replace the commented-out block with a
config-flag-driven version:

```diff
diff --git a/tap_quickbooks/__init__.py b/tap_quickbooks/__init__.py
--- a/tap_quickbooks/__init__.py
+++ b/tap_quickbooks/__init__.py
@@ -15,13 +15,14 @@ def main():
     args = singer.parse_args(required_config_keys)

     config = args.config
-
-    # Disable dev mode: Not supported in Peliqan's singer-python
-    #if args.dev:
-    #    LOGGER.warning("Executing Tap in Dev mode")
-    #client = QuickbooksClient(args.config_path, config, args.dev)
-
-    client = QuickbooksClient(args.config_path, config)
+
+    # dev_mode lets the tap use a pre-issued access_token without rotating the
+    # refresh_token. Toggled via config flag because Peliqan's singer-python
+    # fork doesn't expose `--dev` on the CLI. Used by the regression harness.
+    dev_mode = bool(config.get('dev_mode'))
+    if dev_mode:
+        LOGGER.warning("Executing tap in dev mode (using existing access_token, no refresh)")
+    client = QuickbooksClient(args.config_path, config, dev_mode)
     state = args.state
```

Apply, run the regression, revert when done:

```bash
# Apply (manual edit or git apply with the diff above saved to /tmp/devmode.patch)
git apply /tmp/devmode.patch

# ...run capture + tests (see below)...

# Revert
git checkout -- tap_quickbooks/__init__.py
```

In `dev_mode`:
- The `OAuth2Session` is constructed **without** `auto_refresh_url`, so the
  library physically cannot refresh.
- The pre-issued `access_token` is used directly for every API call.
- The `refresh_token` field is still required by the config schema but is
  never touched.
- Prod's refresh_token chain is **completely safe** — Intuit is never
  called for token operations during the regression run.

The only cost: access_tokens live ~1h. Both `run_capture.sh` and
`run_tests.sh` need to complete inside that window. In practice you grab
the current `access_token` from the prod backend's
`/etc/singer_config/connection_<server_id>/tap_config.json` right after a
successful scheduler run.

## Usage

### Step 1 — Apply the dev_mode patch

See "Patch to apply before testing" above.

### Step 2 — Grab a fresh access_token from prod

SSH onto the prod backend container (or wherever the connection's tap_config.json lives):

```bash
cat /etc/singer_config/connection_<server_id>/tap_config.json
```

Copy the `access_token` value (a JWE starting with `eyJhbGciOiJkaXIi...`).
You have ~1 hour from when prod minted it.

### Step 3 — Export env vars

```bash
export TAP_QUICKBOOKS_CLIENT_ID="ABGFz8HK..."
export TAP_QUICKBOOKS_CLIENT_SECRET="..."        # required by schema, never used in dev_mode
export TAP_QUICKBOOKS_REFRESH_TOKEN="RT1-..."    # required by schema, never used in dev_mode
export TAP_QUICKBOOKS_ACCESS_TOKEN="eyJhbGc..."  # what actually matters
export TAP_QUICKBOOKS_REALM_ID="9341..."
export TAP_QUICKBOOKS_SANDBOX="false"            # optional, default false
export TAP_QUICKBOOKS_INCLUDE_STREAMS="accounts" # optional, default "accounts"
export TAP_QUICKBOOKS_START_DATE="2024-01-01T00:00:00Z"   # optional
```

### Step 4 — Capture baseline (Python 3.9)

Only needed on pre-migration master to (re)generate `baseline/`. The
already-committed baseline was captured against realm `9341453124868055`
with the `accounts` stream (200 records).

```bash
git worktree add /tmp/tap-quickbooks-master master
cp -r tests/regression /tmp/tap-quickbooks-master/tests/regression
cd /tmp/tap-quickbooks-master
git apply /tmp/devmode.patch          # also needed here for the 3.9 run
bash tests/regression/run_capture.sh
cp -r tests/regression/baseline /path/to/migration-branch/tests/regression/
git worktree remove /tmp/tap-quickbooks-master
```

### Step 5 — Run tests (Python 3.11)

```bash
bash tests/regression/run_tests.sh
```

Expected: `6 passed in ~4s`.

### Step 6 — Revert the patch before committing

```bash
git checkout -- tap_quickbooks/__init__.py
```

## Notes

- If you see `AuthenticationFailed` 401s, the `access_token` has expired —
  re-cat the prod tap_config.json and re-run.
- If you see `invalid_grant`, you forgot the patch (the tap is hitting
  Intuit's refresh endpoint).
- Verified working snapshot: Python 3.9.25 ↔ 3.11.15, byte-identical
  output on the `accounts` stream (200 records), `tests/regression/run_tests.sh`
  → 6 passed in 3.67s.
