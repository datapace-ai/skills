# datapace-collector

Pinned version: 0.4.1

Open source (Apache-2.0) on PyPI: https://pypi.org/project/datapace-collector/. Run it with `uvx`, unmodified; only bundles from the unmodified collector may be uploaded. `uvx` brings its own Python. One run reads one provider; for several providers, run once per provider into its own folder.

## AWS

```bash
uvx datapace-collector@0.4.1 --profile <account>=<profile> [--profile …] [--billing-profile <profile>] --regions <r1,r2> --out ./datapace-evidence/aws
```

- Sign-in: the named AWS profiles only. Each must be the 12-digit account it is mapped to (`sts:GetCallerIdentity`).
- `--billing-profile`, optional: a payer profile for Cost Explorer. Without it, Cost Explorer is read from each account.
- Permissions: the nine actions in `iam-policy.json`. The `rds:` and `cloudwatch:` actions in each account; the `ce:` actions on the billing profile, or each account without one.

## Azure

```bash
uvx 'datapace-collector[azure]@0.4.1' --provider azure --subscription <subscription id> [--subscription …] --regions <r1,r2> --out ./datapace-evidence/azure
```

- Sign-in: the user's existing `az login`. For a subscription in another tenant: `az login --tenant <tenant>`.
- Azure roles: `Reader`, `Monitoring Reader`, `Cost Management Reader`, `Reservations Reader`
- `Reader` and `Monitoring Reader` on each subscription; `Cost Management Reader` for cost; `Reservations Reader` for commitments. Only reservations scoped to a named subscription are kept.

## Google Cloud

```bash
uvx 'datapace-collector[gcp]@0.4.1' --provider gcp --project <project id> [--project …] [--billing-dataset <project>.<dataset>] --regions <r1,r2> --out ./datapace-evidence/gcp
```

- Sign-in: application-default credentials (`gcloud auth application-default login`), no key file.
- `--billing-dataset`, optional: the Cloud Billing export to BigQuery. The collector runs one capped query in that project, billed to it (50 GiB scan cap, about USD 0.31). Without it, spend is estimated from list prices.
- Google Cloud roles: `roles/cloudsql.viewer`, `roles/alloydb.viewer`, `roles/monitoring.viewer`, `roles/bigquery.dataViewer`, `roles/bigquery.jobUser`
- The first three on each project; `roles/bigquery.dataViewer` on the export dataset and `roles/bigquery.jobUser` on its project, only with `--billing-dataset`.

## No machine to install uv on

Azure Cloud Shell (`pip install --user uv` first) and Google Cloud Shell (uv preinstalled) are already signed in. Run the same command there, then download the bundle from the Cloud Shell file menu.

## Exit codes

| Code | Meaning                                                                                        |
| ---- | ---------------------------------------------------------------------------------------------- |
| 0    | Bundle written, complete or partial                                                            |
| 1    | Internal error                                                                                 |
| 2    | Usage error (bad flag, unknown profile, missing extra)                                         |
| 3    | Preflight failed, nothing written: sign-in failed, a profile is the wrong account, a subscription is unreadable, or listing databases is denied everywhere |
| 130  | Interrupted; a partial bundle is kept                                                          |

## Output (stderr)

- AWS: `<action> denied for <account> in <region>: <input> will be incomplete` (or `for the billing profile`).
- Azure: `<probe> denied for subscription <id>: needs <role>; <input> will be incomplete`.
- Google Cloud: `<probe> denied for project <id>: needs <role>; …`, and `<api> is not enabled in project <id>; enable it, or <input> will be incomplete`. AlloyDB not enabled only means the project has no AlloyDB.
- `preflight failed: <reason>`: exit 3; the reason names what to fix.
- `wrote <path>`: the bundle, `datapace-bundle-<id>.tgz`.
- `warning: the bundle is <n> MiB, over 64 MiB`: the upload refuses files over 64 MiB.

Every line starts with `datapace-collector: `.

## Bundle

A `.tgz` whose first member is `manifest.json`. Its `provider` names the cloud, and `inputs` maps each input to `{"status", "reason_code"}`; status is `complete`, `partial`, `denied`, `failed` or `not_collected`. Account, subscription and project ids appear only as aliases. `aliases.json` sits beside the bundle, never inside it, and holds the salt: the user keeps it.
