# Datapace skills

Agent skills from [Datapace](https://datapace.ai) for coding agents.

## assess

`/assess` walks you through the Datapace Cloud Self-Assessment: your coding agent runs the open-source [`datapace-collector`](https://pypi.org/project/datapace-collector/) against your own AWS, Azure or Google Cloud databases, and your credentials never leave your machine.

```bash
npx skills add datapace-ai/skills
```

Then type `/assess` in Claude Code, or `$assess` in Codex. Cursor and Gemini CLI pick up the same skill.

The skill may send Datapace anonymous friction reports (the step, a category, a short message, never account ids or names). Set `DATAPACE_SKILL_NO_FEEDBACK=1` to turn them off.

## License

[Apache-2.0](LICENSE)
