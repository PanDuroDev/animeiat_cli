# Contributing

Thanks for your interest in animeiat-cli!

## Branch structure

- **`main`** — stable release branch. Only app source files and documentation.
- **`develop`** — active development. Contains tests, specs, and dev tooling.

## Getting started

```bash
git clone https://github.com/PanDuroDev/animeiat_cli.git
cd animeiat_cli
git checkout develop
pip install -r requirements.txt
playwright install chromium
```

## Code style

- Follow existing patterns (PEP 8).
- Use `os.path.join` for path construction (no `pathlib` for consistency).
- All Rich markup must use `Text.from_markup()` — never raw `Text()`.
- Platform branching uses `os.name` / `sys.platform` checks.

## Before submitting a PR

1. Ensure all tests pass: `pytest tests/ -v`
2. Run `python anime_cli.py --help` and verify no ImportError.
3. Keep the scope focused — one feature/fix per PR.

## Reporting issues

Open an issue at https://github.com/PanDuroDev/animeiat_cli/issues
