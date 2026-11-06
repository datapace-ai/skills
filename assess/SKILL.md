---
name: assess
description: Datapace Cloud Self-Assessment of managed databases (AWS RDS and Aurora), run from Claude Code, Codex, Cursor or Gemini CLI. Checks fit, drafts the read-only IAM policy, runs the open-source datapace-collector on this machine, then hands off to the browser. Use when the user wants to find cost or waste in their cloud databases, or types /assess.
license: Apache-2.0
compatibility: Needs a local coding agent with a shell (Claude Code, Codex, Cursor, Gemini CLI); claude.ai chat cannot run it. Python 3.10+ and uv on the user's machine.
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

> This skill may send anonymous friction reports to Datapace (the step, a category, your agent, the skill version, optionally your cloud provider and database engines, and a short message; never account ids, ARNs, hostnames, paths or names); set `DATAPACE_SKILL_NO_FEEDBACK=1` to turn that off.

Done when the sentence is said.

## 2. Fit check

Ask at most four questions, together, skipping any the user already answered:

1. Which cloud provider?
2. Which database engines?
3. Which accounts and regions?
4. Do they have a payer or billing profile with Cost Explorer access?

Answer from [`references/coverage.md`](references/coverage.md): say which of their engines the assessment covers, partly covers or does not cover.

- **Covered** (at least one `available` row matches): continue.
- **Not covered** (nothing they run is `available`): send one `not_covered` report with their provider and engines (see Feedback), tell them coverage follows these requests and that datapace.ai/assessment lists what is coming, and stop.

Done when you know the provider, the engines, the accounts with a profile name for each, the regions, and whether there is a billing profile.

## 3. Prerequisites

Check, by running them:

- `python3 --version` is 3.10 or later. macOS's system `python3` is 3.9; `uv` brings its own Python, so a recent `uv` is enough.
- `uv --version` works. If it is missing, point to https://docs.astral.sh/uv/getting-started/installation/ and let the user install it.

Profiles: use only the profile names the user gives you, mapped to their 12-digit account ids. Leave `~/.aws` untouched: the collector opens the named profiles itself and checks each one is the account it is mapped to.

Draft the IAM policy from [`references/iam-policy.json`](references/iam-policy.json) as is, for the user to hand to their security team. It grants nine read-only actions: the `rds:` and `cloudwatch:` actions in each account, the `ce:` actions on the billing profile (or each account if there is none). Write it to a file only if the user asks.

Done when Python, uv and the account-to-profile mapping are confirmed and the user has the policy.

## 4. Run

Assemble one command from [`references/collector.md`](references/collector.md), with its pinned version:

```bash
uvx datapace-collector@<pinned> --profile <account>=<profile> [--profile …] [--billing-profile <profile>] --regions <r1,r2> --out ./datapace-evidence
```

Show it, then run it through your normal permission prompt so the user approves it. The collector reports on stderr; read the whole output. Act on the exit code:

- **2, usage:** fix the flag the error names and rerun.
- **3, preflight failed, nothing written:** read the `preflight failed:` line. Either a profile is not the account it is mapped to, or `rds:DescribeDBInstances` is denied everywhere. Tell the user exactly which action to grant in which account (or which mapping to fix), wait for them, rerun.
- **0, bundle written:** go on below. Each `<action> denied for <account> in <region>` line is a grant that would make the bundle more complete: list them as "grant `<action>` in `<account>`" and offer a rerun once granted.
- **1 or 130:** report the error line; send a `blocked` report if the user cannot get past it.

On exit 0, report:

- the bundle path (`datapace-bundle-<id>.tgz` in `./datapace-evidence`) and its size;
- the inputs whose status is not `complete`, from the bundle's `manifest.json` (`inputs`), read with `tar -xOzf <bundle> manifest.json`;
- that `aliases.json` beside the bundle maps the aliases back to real names: the user keeps it and never uploads it.

You read `manifest.json` and the collector output only; `aliases.json` and the other files in the bundle stay unopened. If the bundle is over 64 MiB, say the upload will refuse it and offer a rerun with fewer regions or accounts.

Done when a bundle of 64 MiB or less exists and the user has heard its path, size and partial inputs.

## 5. Hand-off

Give the user:

- the link `https://assess.datapace.ai/sign-up?utm_source=<agent label>&utm_medium=agent&utm_campaign=assessment-skill`;
- the bundle path;
- what comes next: sign up with a work email, accept the terms, create an assessment, drop the file on the upload step; the analysis takes minutes.

Stop there. Return only if the user says the upload was refused: over 64 MiB means a rerun with fewer regions; anything else, read them the app's message and help from it.

## Feedback

At any step, when the user hits something they cannot get past, finds a step confusing, or has an idea, offer to tell Datapace, and send it on their yes. `not_covered` in the fit check needs no extra yes: the consent line covered it.

Send it with [`scripts/feedback.sh`](scripts/feedback.sh), following [`references/feedback.md`](references/feedback.md) for the body and the scrubbing rules. The script does nothing when `DATAPACE_SKILL_NO_FEEDBACK=1` is set. One report per problem.
