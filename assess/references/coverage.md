# Coverage

What the Cloud Self-Assessment reads today. It follows the coverage table on datapace.ai/assessment. `scripts/check_drift.py` fails if a provider marked `available` is one the pinned collector cannot collect.

| Provider     | Engine                                                             | Status              | What the report covers                                                          |
| ------------ | ------------------------------------------------------------------ | ------------------- | ------------------------------------------------------------------------------- |
| AWS          | Amazon RDS for PostgreSQL, MySQL, MariaDB (provisioned, Single-AZ and Multi-AZ) | available           | Idle, downsize, IOPS, storage, gp2 and io1 to gp3, previous generation, extended support |
| AWS          | Amazon Aurora, provisioned (PostgreSQL and MySQL compatible)       | available           | Idle, downsize, I/O-Optimized, replica lag, volume growth, extended support      |
| AWS          | Amazon Aurora Serverless v2                                        | available, partial  | Idle and capacity headroom (ACU) only                                           |
| AWS          | RDS for SQL Server, Oracle, Db2                                    | cost only           | Counted in RDS spend, no savings inferred                                       |
| Azure        | Azure Database for PostgreSQL and MySQL, flexible server           | coming              |                                                                                 |
| Google Cloud | Cloud SQL for PostgreSQL, MySQL and SQL Server                     | coming              |                                                                                 |

Anything not in the table (on-premises, self-managed databases on VMs, MongoDB, Snowflake, Redshift, DynamoDB, other clouds) is not covered.

A user is **covered** when at least one engine they run has an `available` row; `cost only` and `coming` engines alone are **not covered**. Mention the `cost only` and `coming` rows that apply to them either way.

For a `not_covered` report, map what they run to the feedback enums in `feedback.md`: Azure and Google Cloud to `azure` and `gcp`; on-premises to `on_premises`; engines to `postgresql`, `mysql`, `sql_server`, `oracle`, `mongodb`, `snowflake`, else `other`.
