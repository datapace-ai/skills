# Bundle check

What a **good bundle** is, how `scripts/check_bundle.py` tests it, and the **fix loop** that follows. Run it on every bundle the collector writes:

```bash
uv run --no-project python -I scripts/check_bundle.py <bundle> --expect <engine>=<n> [--expect …]
```

`--expect` carries discovery's count of covered databases in scope, per engine key, so the check compares counts, never names. Without discovery, leave it out: the check then only requires at least one database. The script prints one JSON object: `verdict`, `counts`, and `findings`, each with `check`, `severity` (`bad` or `gap`), `code`, `detail`, `action` and, when the collector gave one, `reason_code`. It prints no row of the bundle and nothing from `aliases.json`.

## Engine keys

| Provider     | Key                                                                                                                   | From discovery                                                       |
| ------------ | --------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------- |
| AWS          | the RDS `Engine` as is: `postgres`, `mysql`, `mariadb`, `aurora-postgresql`, `aurora-mysql`, …                         | `describe-db-instances`, one per instance, Aurora instances included |
| Azure        | `postgresql`, `mysql` (flexible servers), `sql_database` (single databases, not `master`), `sql_managed_instance`      | `az resource list` types, `az sql db list`                           |
| Google Cloud | `postgres`, `mysql`, `sqlserver` (the `databaseVersion` before its first `_`), `alloydb` (instances)                  | `gcloud sql instances list`, `gcloud alloydb instances list`         |

Count only databases in the regions and scopes the command collects.

## Criteria

Thresholds come from datapace-platform, `src/datapace/domain/assessment/rules/`: `series.py` (`MIN_SPAN_DAYS = 14`, `MIN_SAMPLE_PERCENT = 80`), `measure.py` (`rerun_after_days`), `capabilities.py` and `report.py` (the gap a report shows per input). Core metrics are the ones each provider's `idle` rule reads: `utilisation.py`, `azure/utilisation.py`, `azure/sql_database.py`, `azure/managed_instance.py`, `gcp/utilisation.py`, `gcp/alloydb.py`. The upload limit is 64 MiB. When the platform changes them, change `check_bundle.py` with them.

| Check       | Bad                                                                                                    | Gap                                                                                                    |
| ----------- | ------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------ |
| Integrity   | unreadable, a listed artifact absent, a sha256 or size mismatch, an artifact not JSON, over 64 MiB      |                                                                                                        |
| Inventory   | fewer databases of an engine than discovery found; no database at all                                   | inventory not `complete`, counts still match                                                            |
| Metrics     | databases but no series at all                                                                         | a database lacks a core metric; a core series spans under 14 days (`rerun_after_days`); under 80 % of hourly samples |
| Spend       |                                                                                                        | databases but no cost row (`spend_empty`; `spend_list_price` on Google Cloud without `--billing-dataset`); an Azure server with no cost row; costs not `complete` |
| Commitments |                                                                                                        | reservations or coverage not `complete`                                                                 |
| Privacy     | a raw account, subscription or project id, or a resource name from `aliases.json`, appears in the bundle |                                                                                                        |

Status and content are checked together: a `complete` input with no rows is judged by its content, which is the 2026-11-09 Azure case (costs `complete`, `{"daily":[]}`).

## Verdicts

- **good:** no finding. Hand off.
- **good_with_gaps:** gaps only. Explain each gap and its cause in a line; hand off when the user agrees to upload anyway.
- **bad:** at least one `bad` finding. Go to the fix loop.

## Fix loop

At most two automatic reruns after the first run. Each finding's `action` and `reason_code`, read with what discovery saw, give one move:

| Action         | Cause                                                                                   | Move                                                                                                     |
| -------------- | --------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| `fix_flags`    | a scope, region or project flag left a database out                                      | correct the command from discovery and rerun on your own                                                  |
| `rerun`        | `throttled`, `service_error`, `cancelled`, a broken bundle                               | rerun as is                                                                                              |
| `rerun_smaller`| over 64 MiB                                                                              | rerun with fewer regions or scopes, one bundle each                                                       |
| `user_command` | local sign-in or config: on Google Cloud, `not_enabled` on inventory while `gcloud` or billing shows the databases means the application-default quota project; an expired sign-in | give the exact command (`gcloud auth application-default set-quota-project <target project>`, `az login`, `aws sso login --profile <p>`); rerun once the user says it is done |
| `grant`        | `access_denied`, or an API that really is not enabled                                    | draft the grant or the enablement for the user or their security team, from `collector.md`; you never change cloud config. Rerun once granted |
| `wait`         | metrics under 14 days                                                                   | nothing to fix now: rerun after `rerun_after_days`                                                        |
| `explain`      | a known gap: empty spend on an Azure subscription whose `quotaId` starts with `CSP`, no billing export on Google Cloud, no commitments | say why and whether a rerun can help                                                                      |
| `report`       | a raw id in the bundle: a collector bug                                                  | do not upload; send a `blocked` report                                                                     |

Every finding with `wait`, `explain` or `report`, and every rerun, is sent as a friction report (`feedback.md`).

After the last attempt, state the verdict plainly and name the one bundle to upload per provider: the newest one. Earlier bundles in the same `--out` folder are superseded; say so.
