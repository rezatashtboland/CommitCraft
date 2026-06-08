# Commit Message Structure

CommitCraft prompts the AI model to produce commit messages in this structure:

```text
type: short summary

- Optional short detail
- Optional short detail
```

Allowed commit types:

- `feat`
- `fix`
- `docs`
- `style`
- `refactor`
- `test`
- `chore`
- `perf`
- `ci`
- `build`

The model output language is configured independently from the terminal UI language.
