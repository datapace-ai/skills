# datapace-collector

Pinned version: 0.3.0

Open source (Apache-2.0) on PyPI: https://pypi.org/project/datapace-collector/. Run it as `uvx datapace-collector@0.3.0 …`, unmodified: only bundles from the unmodified collector may be uploaded.

## Flags (AWS)

- `--profile ACCOUNT=PROFILE`, repeatable, required: a 12-digit account id and the local AWS profile for it. Only these profiles are opened. Each must really be that account (`sts:GetCallerIdentity`) or the run exits 3.
- `--billing-profile PROFILE`, optional: a payer profile for Cost Explorer. Lines for accounts not named are dropped. Without it, Cost Explorer is read from each account.
- `--regions r1,r2`, required: comma-separated AWS regions.
- `--out DIR`, required: where the bundle and `aliases.json` are written. Rerunning into the same folder keeps aliases stable.

## Exit codes

| Code | Meaning                                                                                   |
| ---- | ----------------------------------------------------------------------------------------- |
| 0    | Bundle written, complete or partial                                                       |
| 1    | Internal error                                                                            |
| 2    | Usage error (bad flag, unknown profile)                                                   |
| 3    | Preflight failed, nothing written: a profile is the wrong account, cannot be confirmed, or `rds:DescribeDBInstances` is denied in every account and region |
| 130  | Interrupted; a partial bundle is kept                                                     |

## Output (stderr)

- `datapace-collector: <action> denied for <account> in <region>: <input> will be incomplete` (or `for the billing profile`): one per denied probe; the run goes on.
- `datapace-collector: preflight failed: <reason>`: exit 3.
- `datapace-collector: wrote <path>`: the bundle, `datapace-bundle-<id>.tgz`.
- `datapace-collector: warning: the bundle is <n> MiB, over 64 MiB`: the upload refuses files over 64 MiB.

## Bundle

A `.tgz` whose first member is `manifest.json`. Its `inputs` maps each input (`inventory`, `costs`, `coverage`, `reservations`, `snapshots`, `metrics`) to `{"status", "reason_code"}`; status is `complete`, `partial`, `denied`, `failed` or `not_collected`. Account ids appear only as aliases. `aliases.json` sits beside the bundle, never inside it, and holds the salt: the user keeps it.
