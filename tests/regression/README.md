# tap-quickbooks — Python 3.11 Regression Tests

Before/after parity test for the Python 3.9 → 3.11 migration.

## Strategy

1. **Capture** baseline on pre-migration `master` + Python 3.9: discover, select all streams, sync, record schemas / state-key names / record field names.
2. **Compare** on migration branch + Python 3.11 — assert schemas unchanged, no streams dropped, all baseline fields still present.

## Files

| File | Purpose |
| --- | --- |
| `conftest.py` | Shared fixtures: config builder, discover + select_all, sync runner, message parser |
| `capture.py` | Standalone — run once on Python 3.9 to write `baseline/` |
| `test_regression.py` | pytest suite — run on Python 3.11 to verify parity |
| `run_capture.sh` | Wrapper that runs `capture.py` in `python:3.9-slim` Docker |
| `run_tests.sh` | Wrapper that runs pytest in `python:3.11-slim` Docker |
| `baseline/` | Committed reference output: schemas, state keys, record fields, catalog, meta |

## Why `dev_mode`?

QuickBooks rotates the refresh_token on **every** call to Intuit's
`/oauth2/v1/tokens/bearer` endpoint. If the regression harness used the standard
refresh flow, every test run would consume a token off the same lineage prod's
scheduler also uses — racing prod and possibly causing its next sync to
`invalid_grant`.

The tap already has a `dev_mode` branch in `tap_quickbooks/client.py:147-166`
that bypasses the refresh endpoint entirely and uses a pre-issued
`access_token`. The branch was previously CLI-gated via `--dev` (commented
out because Peliqan's fork of singer-python doesn't expose `args.dev`); we
re-enabled it via a config field `dev_mode: true` in
`tap_quickbooks/__init__.py`.

In dev_mode:
- The `OAuth2Session` is constructed **without** `auto_refresh_url`, so the
  library physically cannot refresh.
- The pre-issued `access_token` is used directly for every API call.
- The `refresh_token` field is still required by the config schema but is
  never touched.
- Prod's refresh_token chain is **completely safe** — Intuit is never called
  for token operations during the regression run.

The only cost: access_tokens live ~1h. Both `run_capture.sh` and
`run_tests.sh` need to complete inside that window. In practice you grab the
current `access_token` from the prod backend's
`/etc/singer_config/connection_<server_id>/tap_config.json` right after a
successful scheduler run.

## Usage

Required env vars:

```bash
export TAP_QUICKBOOKS_CLIENT_ID=...
export TAP_QUICKBOOKS_CLIENT_SECRET=...        # the encrypted envelope from prod is fine; never used in dev_mode
export TAP_QUICKBOOKS_REFRESH_TOKEN=...        # required by tap config schema; never used in dev_mode
export TAP_QUICKBOOKS_ACCESS_TOKEN="eyJhbGc..." # current JWE token from prod tap_config.json
export TAP_QUICKBOOKS_REALM_ID="9341..."
export TAP_QUICKBOOKS_SANDBOX="false"          # optional, default false
export TAP_QUICKBOOKS_START_DATE="2024-01-01T00:00:00Z"   # optional
```

### Capture baseline (pre-migration code on Python 3.9)

```bash
git worktree add /tmp/tap-quickbooks-master master
cp -r tests/regression /tmp/tap-quickbooks-master/tests/regression
cd /tmp/tap-quickbooks-master
bash tests/regression/run_capture.sh
cp -r tests/regression/baseline /path/to/migration-branch/tests/regression/
git worktree remove /tmp/tap-quickbooks-master
```

### Run tests (migration branch on Python 3.11)

```bash
bash tests/regression/run_tests.sh
```

## Notes

- The dev_mode config flag is read in `tap_quickbooks/__init__.py`. The
  switch lives in plain config — no CLI changes needed.
- If you see `AuthenticationFailed` 401s, the `access_token` has expired —
  re-cat the prod tap_config.json and re-run.
