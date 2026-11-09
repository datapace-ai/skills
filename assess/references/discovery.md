# Discovery

What you run, on the user's yes, to find out what the collector can get on one provider before it runs. Every command here only reads. Run them as written, with their prompt-off flag (`--quiet`, `--only-show-errors`): a command that asks a question, offers to enable an API or install an extension gets the answer no. Each command is one call per account, subscription, project or region in scope; batch a provider's commands into one shell call where your permission prompt allows.

The fixes you find (a sign-in, a quota project, a role, an API) go to the user as exact commands for them to run; discovery itself changes nothing.

## Output

Show one table per provider, then the proposed command:

| Scope | Databases (covered / partial / not covered) | Inventory | Metrics | Costs | Why partial |
| ----- | ------------------------------------------- | --------- | ------- | ----- | ----------- |

- One row per account, subscription or project that has databases, with the regions they are in. Engines are matched against `coverage.md`.
- Inventory, Metrics and Costs: `complete`, `partial` or `none`, as you expect the collector to get them.
- **Why partial** names the fix: the missing role and where, the API to enable and where, the sign-in, the CSP subscription, the missing billing export.
- Under the table, name the scopes skipped because they hold no database, in one line.
- The proposed command is the provider's command from `collector.md` with the scope filled in: only the scopes with databases, only their regions, and the billing flag when billing access was found. The user approves it; it is what step 4 runs.

Keep the counts and the per-scope expectations: step 4's content check compares the bundle against them.

## AWS

1. **Sign-in.** `aws configure list-profiles`, then for each profile the user names, or each one if they asked you to look: `aws sts get-caller-identity --profile <p> --query Account --output text`. An expired SSO session needs `aws sso login --profile <p>`, which the user runs.
2. **Regions.** The user's, else `aws ec2 describe-regions --profile <p> --query 'Regions[].RegionName' --output text`. If that is denied, ask for the regions.
3. **Databases**, per profile and region:
   - `aws rds describe-db-instances --profile <p> --region <r> --query 'DBInstances[].[Engine,DBInstanceClass,MultiAZ]' --output text`
   - `aws rds describe-db-clusters --profile <p> --region <r> --query 'DBClusters[].[Engine,EngineMode,ServerlessV2ScalingConfiguration.MaxCapacity]' --output text` (a capacity means Aurora Serverless v2).
4. **Billing.** One Cost Explorer call from the billing profile the user names, else from each account (USD 0.01 per call): `aws ce get-cost-and-usage --profile <p> --time-period Start=<first of last month>,End=<first of this month> --granularity MONTHLY --metrics UnblendedCost --query 'ResultsByTime[].Total.UnblendedCost.Amount' --output text`. A member account of an organization often sees nothing: Costs is `partial` until a payer profile is given.
5. **Gaps.** An `AccessDenied` maps to the action in `iam-policy.json` it names. `cloudwatch:GetMetricData` is not probed here: the collector's preflight reports it.

## Azure

Prefix each `az` command with `AZURE_EXTENSION_USE_DYNAMIC_INSTALL=no` and add `--only-show-errors`, so no extension is installed.

1. **Sign-in.** `az account show --query '{user:user.name,tenant:tenantId}' -o json`. Not signed in or expired: the user runs `az login`, or `az login --tenant <tenant>` for a subscription in another tenant.
2. **Subscriptions.** `az account list --all --query "[?state=='Enabled'].{id:id,name:name,tenant:tenantId}" -o json`, then each one's offer: `az rest --method get --url "https://management.azure.com/subscriptions/<id>?api-version=2022-12-01" --query subscriptionPolicies.quotaId -o tsv`. A `quotaId` starting with `CSP` is a Cloud Solution Provider subscription: the customer sees cost only if the partner turned on the cost visibility policy, so warn that Costs may come back empty.
3. **Databases**, per subscription: `az resource list --subscription <id> --query "[?starts_with(type,'Microsoft.DBforPostgreSQL/') || starts_with(type,'Microsoft.DBforMySQL/') || starts_with(type,'Microsoft.Sql/') || starts_with(type,'Microsoft.DocumentDB/') || starts_with(type,'Microsoft.Cache/')].{type:type,kind:kind,location:location,sku:sku.tier}" -o json`. It names the regions too. For each SQL server with databases, the tier decides the coverage row: `az sql db list --subscription <id> --resource-group <rg> --server <server> --query "[].{tier:currentSku.tier,kind:kind,pool:elasticPoolName}" -o json` (`serverless` in `kind`, `Hyperscale` tier, a `pool`).
4. **Billing.** One Cost Management query per subscription, a read sent as POST: `az rest --method post --url "https://management.azure.com/subscriptions/<id>/providers/Microsoft.CostManagement/query?api-version=2023-03-01" --body '{"type":"ActualCost","timeframe":"MonthToDate","dataset":{"granularity":"None","aggregation":{"cost":{"name":"Cost","function":"Sum"}}}}' --query properties.rows -o json`. Denied: `Cost Management Reader` is missing. Empty rows on a subscription with databases: Costs is `partial`, the CSP case above or a cost visibility setting.
5. **Gaps.** The probes stand in for the roles: the resource list needs `Reader`, the cost query `Cost Management Reader`. `Monitoring Reader`: `az monitor metrics list-definitions --resource <one database's id> --query 'length(@)'`. `Reservations Reader`: `az rest --method get --url "https://management.azure.com/providers/Microsoft.Capacity/reservationOrders?api-version=2022-11-01" --query 'length(value)'`; denied only means commitments are left out.

## Google Cloud

Add `--quiet` to each `gcloud` command and run `bq` as `bq --headless --quiet`.

1. **Sign-in.** `gcloud auth list --filter=status:ACTIVE --format='value(account)' --quiet` for the CLI, and `gcloud auth application-default print-access-token --quiet > /dev/null` for the application-default credentials the collector uses. Either failing: the user runs `gcloud auth login` or `gcloud auth application-default login`.
2. **Quota project.** The collector bills its API calls to the application-default quota project. Read only that key: `uv run --no-project python -I -c "import json,os;p=os.environ.get('CLOUDSDK_CONFIG') or os.path.expanduser('~/.config/gcloud');print(json.load(open(os.path.join(p,'application_default_credentials.json'))).get('quota_project_id',''))"` (on Windows the folder is `%APPDATA%\gcloud`). If it is not one of the target projects, check it has `sqladmin.googleapis.com` enabled (step 4); if not, the collector will report the Cloud SQL API off everywhere. The fix, for the user to run: `gcloud auth application-default set-quota-project <target project>`.
3. **Projects.** The user's, else `gcloud projects list --format='value(projectId)' --limit=200 --quiet`.
4. **APIs**, per project: `gcloud services list --enabled --project <p> --filter='config.name:(sqladmin.googleapis.com alloydb.googleapis.com monitoring.googleapis.com bigquery.googleapis.com)' --format='value(config.name)' --quiet`. Denied: skip it, the database listings below tell you the same.
5. **Databases**, per project:
   - `gcloud sql instances list --project <p> --format='value(databaseVersion,region,settings.tier,settings.availabilityType)' --quiet`
   - `gcloud alloydb instances list --project <p> --cluster=- --region=- --format='value(instanceType,machineConfig.cpuCount,name.segment(3))' --quiet`, only where `alloydb.googleapis.com` is enabled.
6. **Billing export.** `gcloud billing projects describe <p> --format='value(billingAccountName)' --quiet` names the billing account. The export lives in a BigQuery dataset, often in a separate project the user knows: list the datasets of the target projects and of any project the user names, `bq --headless --quiet ls --max_results=50 --project_id=<p>`, then the tables of each, `bq --headless --quiet ls --max_results=200 <p>:<dataset>`, and look for `gcp_billing_export_v1_` or `gcp_billing_export_resource_v1_`. Found: `--billing-dataset <p>.<dataset>`. Not found: Costs is estimated from list prices, say so.
7. **Gaps.** A denied listing maps to its role in `collector.md`: `roles/cloudsql.viewer`, `roles/alloydb.viewer`; `roles/monitoring.viewer` is checked by the collector's preflight. An API not enabled is named with its project; enabling it is the user's call.
