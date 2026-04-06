# Contributing to ha-drone-mobile

## Development Setup

1. Clone the repository:
   ```bash
   git clone git@github.com:HolyBitsLLC/ha-drone-mobile.git
   cd ha-drone-mobile
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements-dev.txt
   pip install -e .
   ```

## Testing

Run the full test suite:
```bash
pytest --cov=custom_components/drone_mobile tests/
```

## Linting

```bash
ruff check custom_components/ tests/
```

## CI Requirements

All PRs must pass:
- **Lint** — `ruff check` with no errors
- **Test** — `pytest` with all tests passing
- **HACS Validation** — `hacs/action` validates the integration structure

## Release Process

1. Update `version` in `custom_components/drone_mobile/manifest.json`
2. Tag the commit: `git tag v1.0.0`
3. Push the tag: `git push origin v1.0.0`
4. GitHub Actions will create the release automatically

## Code Style

- Python 3.12+
- Follow Home Assistant integration best practices
- Use type hints throughout
- Use `ruff` for formatting and linting

## Commit Messages

Use descriptive commit messages, optionally prefixed:
- `feat:` — new features
- `fix:` — bug fixes
- `docs:` — documentation changes
- `test:` — test additions/changes
- `chore:` — maintenance tasks
