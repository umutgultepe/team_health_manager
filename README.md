# Team Health Reporter

A CLI tool for reporting team health metrics.

## Installation

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install the package in development mode:
```bash
pip install -e .
```

## Usage

After installation, you can use the `health` command:

```bash
health report
```

## Development

### Running Tests

```bash
pytest
```

### Project Structure

```
.
├── src/
│   └── health/
│       └── cli.py
├── tests/
├── pyproject.toml
└── README.md
```

## License

MIT 