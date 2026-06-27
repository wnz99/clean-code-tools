# Sample Apps

These apps exercise the clean-code lint presets against realistic small examples.

## Python

```bash
python -m pip install "ruff>=0.15.0" "pylint>=4.0.0"
cd sample-apps/python-app
ruff check src/clean_pricing.py
pylint --rcfile=pyproject.toml src/clean_pricing.py
ruff check src/smelly_pricing.py
pylint --rcfile=pyproject.toml src/smelly_pricing.py
```

The clean file should pass. The smelly file should report TODO tracking, commented-out code, unused arguments, and too many arguments.

## TypeScript Backend

```bash
cd sample-apps/ts-backend
npm install
npm run lint:clean
npm run lint:smelly
```

The clean handler should pass. The smelly handler should report untracked TODOs, commented-out code, boolean flag arguments, policy literals, train-wreck navigation, and null usage.

## TypeScript Frontend

```bash
cd sample-apps/ts-frontend
npm install
npm run lint:clean
npm run lint:smelly
```

The clean widget should pass. The smelly widget should report untracked TODOs, commented-out code, train-wreck navigation, policy literals, output argument mutation, null usage, and boolean flag arguments.

The TypeScript samples import the preset through `clean-code-tools/configs/eslint.clean-code.recommended.mjs`, so they exercise the package export path rather than a repository-relative config path.
