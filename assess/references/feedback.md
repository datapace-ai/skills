# Feedback

Anonymous reports to Datapace, sent with `scripts/feedback.sh '<json body>'`. The script adds `skillVersion`, skips sending when `DATAPACE_SKILL_NO_FEEDBACK=1`, refuses a body that looks like it carries an identifier, and prints the HTTP status (204 is sent; 429 is the daily limit, drop it).

## Body

JSON, camelCase, no other keys:

| Key            | Required | Values                                                                 |
| -------------- | -------- | ---------------------------------------------------------------------- |
| `category`     | yes      | `blocked`, `not_covered`, `confusing`, `idea`                          |
| `step`         | yes      | `fit`, `prerequisites`, `preflight`, `collect`, `handoff`, `other`     |
| `agent`        | yes      | `claude-code`, `codex`, `cursor`, `gemini-cli`, `other`                |
| `provider`     | no       | `aws`, `azure`, `gcp`, `on_premises`, `other`                          |
| `technologies` | no       | array of `postgresql`, `sql_server`, `mysql`, `oracle`, `mongodb`, `snowflake`, `other` |
| `message`      | no       | plain text, 500 characters at most                                     |

Steps: `fit` is the fit check, `prerequisites` covers Python, uv, profiles and the policy, `preflight` is an exit 3, `collect` is a failure after preflight, `handoff` is the link and the upload.

Example, for a user on Azure SQL Database and Cosmos DB:

```bash
scripts/feedback.sh '{"category":"not_covered","step":"fit","agent":"codex","provider":"azure","technologies":["sql_server","other"],"message":"Azure SQL Database and Cosmos DB"}'
```

## Scrubbing

The message says what happened in general words: the step, the action or error class, the engine. Write it so it would read the same for any company. Replace every account id, ARN, hostname, endpoint, IP address, file path, profile name, resource name, person's name and company name with a generic word ("an account", "the billing profile").
