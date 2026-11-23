# Development workflow

- Work happens on short-lived feature branches named `vibe/<short-slug>-a5d49e`.
- Pull requests are opened from those branches against `main` and stay **draft** until
  they have been tested on a real Home Assistant instance. Only then are they merged.
- Delete feature branches once merged.

## Local checks before pushing

```bash
python scripts/validate_integration.py
python -m pytest tests/test_parse.py -q   # no Home Assistant needed
python -m pytest tests -q                 # all tests, needs `pip install homeassistant`
```

CI (`.github/workflows/ci.yml`) runs the same checks on every push and PR.
