---
name: assess
description: Datapace Cloud Self-Assessment of managed databases on AWS, Azure and Google Cloud, run from Claude Code, Codex, Cursor or Gemini CLI. Checks fit, drafts the read-only permissions, runs the open-source datapace-collector on this machine, then hands off to the browser. Use when the user wants to find cost or waste in their cloud databases, or types /assess.
license: Apache-2.0
compatibility: Needs a local coding agent with a shell (Claude Code, Codex, Cursor, Gemini CLI); claude.ai chat cannot run it. uv on the user's machine.
metadata:
  version: "0.1.0" # x-release-please-version
---

# assess

You guide the user through the Datapace Cloud Self-Assessment. Everything you do is read-only and local: the collector runs on this machine with the user's own access, and the bundle stays here until the user uploads it in the browser. Credentials never leave this machine.

You are the **guide**: you ask, draft, run and explain. Sign-up, terms, upload and the report happen in the browser, by the user.

Your **agent label** is the one that names you: `claude-code`, `codex`, `cursor` or `gemini-cli`, else `other`. It goes in the hand-off link and in feedback.

If you have no shell on the user's machine (for example claude.ai chat), say the skill needs a local coding agent, give the install lines from the repository README, and stop.

## 1. Consent line

Say this first, before anything else, in one sentence:

> This skill may send anonymous friction reports to Datapace (the step, a category, your agent, the skill version, optionally your cloud provider and database engines, and a short message; never account, subscription or project ids, ARNs, hostnames, paths or names); set `DATAPACE_SKILL_NO_FEEDBACK=1` to turn that off.

Done when the sentence is said.

## 2. Fit check

Ask at most four questions, together, skipping any the user already answered:

1. Which cloud providers?
2. Which database engines?
3. Which accounts, subscriptions or projects, and which regions?
4. Billing access: on AWS, a payer profile with Cost Explorer; on Azure, Cost Management Reader; on Google Cloud, a Cloud Billing export to BigQuery?

Answer from [`references/coverage.md`](references/coverage.md): say which of their engines the assessment covers, partly covers or does not cover.

- **Covered** (at least one `available` row matches): continue with the covered providers. If they also run something not covered, send one `not_covered` report for it.
- **Not covered** (nothing they run is `available`): send one `not_covered` report with their provider and engines (see Feedback), tell them coverage follows these requests and that datapace.ai/assessment lists what is coming, and stop.

Done when you know, for each covered provider: the engines; the AWS accounts with a profile name for each, the Azure subscription ids or the Google Cloud project ids; the regions; and the billing access.

## 3. Prerequisites

Check `uv --version` works. If it is missing, point to https://docs.astral.sh/uv/getting-started/installation/ and let the user install it; `uv` brings its own Python. A user who cannot install anything can run the collector in Azure Cloud Shell or Google Cloud Shell (see [`references/collector.md`](references/collector.md)).

Sign-in stays with the user, per provider:

- **AWS:** use only the profile names the user gives you, mapped to their 12-digit account ids. Leave `~/.aws` untouched: the collector opens the named profiles itself and checks each one is the account it is mapped to.
- **Azure:** the user is signed in with `az login`, to the tenant of each subscription.
- **Google Cloud:** the user has run `gcloud auth application-default login`.

Draft the read-only permissions for the user to hand to their security team:

- **AWS:** [`references/iam-policy.json`](references/iam-policy.json) as is: nine read-only actions.
- **Azure and Google Cloud:** the role list and where each role applies, from [`references/collector.md`](references/collector.md).

Write them to a file only if the user asks.

Done when uv and each provider's sign-in are confirmed and the user has the permissions.

## 4. Run

For each covered provider, assemble its command from [`references/collector.md`](references/collector.md), with the pinned version and its own `--out` folder. Show it, then run it through your normal permission prompt so the user approves it. The collector reports on stderr; read the whole output. Act on the exit code:

- **2, usage:** fix the flag the error names and rerun.
- **3, preflight failed, nothing written:** read the `preflight failed:` line and tell the user exactly what to fix: the sign-in, the mapping, or which permission to grant where. Wait for them, rerun.
- **0, bundle written:** go on below. Each `denied` line is a grant that would make the bundle more complete: list them as "grant `<action or role>` on `<account, subscription or project>`" and offer a rerun once granted. A Google Cloud API that is not enabled is the same: name the API and the project.
- **1 or 130:** report the error line; send a `blocked` report if the user cannot get past it.

On exit 0, report:

- the bundle path (`datapace-bundle-<id>.tgz` in the `--out` folder) and its size;
- the inputs whose status is not `complete`, from the bundle's `manifest.json` (`inputs`), read with `tar -xOzf <bundle> manifest.json`;
- that `aliases.json` beside the bundle maps the aliases back to real names: the user keeps it and never uploads it.

You read `manifest.json` and the collector output only; `aliases.json` and the other files in the bundle stay unopened. If a bundle is over 64 MiB, say the upload will refuse it and offer a rerun with fewer regions, accounts, subscriptions or projects.

Done when each covered provider has a bundle of 64 MiB or less and the user has heard its path, size and partial inputs.

## 5. Hand-off

Give the user:

- the link `https://assess.datapace.ai/sign-up?utm_source=<agent label>&utm_medium=agent&utm_campaign=assessment-skill`;
- the bundle paths;
- what comes next: sign up with a work email, accept the terms, create an assessment, drop the files on the upload step (one assessment takes a bundle per provider and merges them into one report); the analysis takes minutes.

Stop there. Return only if the user says the upload was refused: over 64 MiB means a rerun with a smaller scope; anything else, read them the app's message and help from it.

## Feedback

At any step, when the user hits something they cannot get past, finds a step confusing, or has an idea, offer to tell Datapace, and send it on their yes. `not_covered` in the fit check needs no extra yes: the consent line covered it.

Send it with [`scripts/feedback.sh`](scripts/feedback.sh), following [`references/feedback.md`](references/feedback.md) for the body and the scrubbing rules. The script does nothing when `DATAPACE_SKILL_NO_FEEDBACK=1` is set. One report per problem.
