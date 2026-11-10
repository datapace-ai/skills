# Datapace skills

Agent skills from [Datapace](https://datapace.ai) for coding agents.

## assess

`/assess` walks you through the Datapace Cloud Self-Assessment: your coding agent runs [`datapace-collector`](https://pypi.org/project/datapace-collector/) (Apache-2.0, source in the PyPI source distribution) against your own AWS, Azure or Google Cloud databases, and your credentials never leave your machine.

```bash
npx skills add datapace-ai/skills
```

Then type `/assess` in Claude Code, or `$assess` in Codex. Cursor and Gemini CLI pick up the same skill.

In Claude Code you can also install it as a plugin:

```text
/plugin install assess --marketplace datapace-ai/skills
```

By default the skill sends Datapace an anonymous report on how each run goes, good or bad: the step, a category, your agent, the skill version, optionally your cloud provider and database engines, the collector version and which data inputs it collected, and a short message. It never sends account, subscription or project ids, ARNs, hostnames, paths or names. Tell your agent no at any time, or set `DATAPACE_SKILL_NO_FEEDBACK=1`, and nothing more is sent.

## License

[Apache-2.0](LICENSE)
