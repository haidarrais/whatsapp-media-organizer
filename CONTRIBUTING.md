# Contributing to WhatsApp Media Organizer

Thanks for taking the time to contribute! We welcome bug reports, feature
requests, documentation improvements, and pull requests.

## Getting started

1. Fork the repository and clone your fork.
2. Install in editable mode with the test extras:

   ```bash
   python -m pip install -e ".[test]"
   ```

3. Run the test suite before and after your changes:

   ```bash
   python -m pytest
   ```

## Development workflow

- Keep changes small and focused. One logical change per pull request.
- The core module (`src/whatsapp_media_organizer/core.py`) must stay
  **dependency-free** (standard library only). This is what lets the CLI, the
  GUI, and the packaged binaries all share the same logic.
- Use `Path` objects and `os.path.join` / `/` for paths so the code behaves on
  Windows and macOS alike.
- Add or update tests in `tests/` for any behavior change. Tests are
  `tmp_path`-based and use only the standard library plus pytest.
- Run `ruff check src tests` and fix anything it flags before pushing.

## Commit conventions

We follow the [Conventional Commits](https://www.conventionalcommits.org/)
style:

- `feat:` — new feature
- `fix:` — bug fix
- `docs:` — documentation
- `refactor:` — code change that neither fixes a bug nor adds a feature
- `test:` — tests
- `chore:` — build, tooling, housekeeping

## Release process

Releases are cut from `main` by tagging a commit:

```bash
git tag v0.1.0
git push origin v0.1.0
```

CI then builds platform binaries with PyInstaller and publishes a GitHub
Release with the EXE / DMG / Linux binary attached.

## Code of conduct

All contributors must follow our [Code of Conduct](CODE_OF_CONDUCT.md).
