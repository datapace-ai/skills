# Coverage

What the Cloud Self-Assessment reads, from the Coverage List version 2026-11-07 (assess.datapace.ai/coverage). `scripts/check_drift.py` fails if a provider marked `available` is one the pinned collector cannot collect.

| Provider     | Engine                                                                  | Status             | Note                                                         |
| ------------ | ----------------------------------------------------------------------- | ------------------ | ------------------------------------------------------------ |
| AWS          | Amazon RDS for PostgreSQL, MySQL and MariaDB, provisioned, Single-AZ and Multi-AZ | available          |                                                              |
| AWS          | Amazon Aurora, provisioned, PostgreSQL and MySQL compatible             | available          |                                                              |
| AWS          | Amazon Aurora Serverless v2                                             | available, partial | Idle and capacity headroom only                              |
| AWS          | Amazon RDS for SQL Server, Oracle and Db2                               | cost only          | Counted in spend, no savings inferred                        |
| Azure        | Azure Database for PostgreSQL, flexible server                          | available          |                                                              |
| Azure        | Azure Database for MySQL, flexible server                               | available          |                                                              |
| Azure        | Azure SQL Database, single database, provisioned vCore or DTU           | available          | Includes the Azure Hybrid Benefit saving                     |
| Azure        | Azure SQL Database, serverless                                          | available, partial | Storage and zone redundancy only                             |
| Azure        | Azure SQL Database, Hyperscale                                          | available, partial | No saving amounts                                            |
| Azure        | Azure SQL Database in an elastic pool                                   | cost only          | Counted in spend, no savings inferred                        |
| Azure        | Azure SQL Managed Instance, General Purpose and Business Critical       | available, partial | No idle check                                                |
| Google Cloud | Cloud SQL for PostgreSQL, MySQL and SQL Server                          | available          |                                                              |
| Google Cloud | AlloyDB for PostgreSQL, primary and read pool instances                 | available, partial | Idle, downsize, HA premium, committed use; savings on N2 only |

Not covered: anything not in the table, for example Spanner, Memorystore, Cosmos DB, Redshift, DynamoDB, MongoDB, Snowflake, self-managed databases on VMs, on-premises and other clouds.

A user is **covered** when at least one engine they run has an `available` row; `cost only` engines alone are **not covered**. Mention the partial and `cost only` rows that apply to them either way.

For a `not_covered` report, map what they run to the feedback enums in `feedback.md`: provider `aws`, `azure`, `gcp`, `on_premises`, else `other`; engines `postgresql`, `mysql`, `sql_server`, `oracle`, `mongodb`, `snowflake`, else `other`.
