# Team Health Reporter

A CLI tool for reporting team health metrics, designed to help teams track and analyze their health metrics over time.

## Features

- Automated health metric reporting
- Integration with Google Sheets for data storage
- Slack notifications for report updates
- Retry mechanism for API rate limits
- Configurable through YAML files

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/team-health-reporter.git
cd team-health-reporter
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install the package in development mode:
```bash
pip install -e .
```

4. Install dependencies:
```bash
pip install -r requirements.txt
```

## Configuration

1. Set up your Google Sheets API credentials:
   - Create a service account in Google Cloud Console
   - Download the credentials JSON file
   - Place it in the appropriate location as specified in your config

2. Configure Slack integration:
   - Create a Slack app
   - Get the bot token
   - Add it to your configuration

3. Update the configuration files:
   - `config/credentials.yaml` for API keys and tokens
   - `config/settings.yaml` for general settings

## Usage

After installation and configuration, you can use the `health` command:

```bash
# Generate a health report
health report

# View help
health --help
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
│       ├── cli.py
│       ├── clients/
│       │   ├── sheets.py
│       │   └── slack.py
│       ├── config/
│       │   ├── credentials.py
│       │   └── settings.py
│       └── utils/
│           └── date.py
├── tests/
├── config/
│   ├── credentials.yaml
│   └── settings.yaml
├── pyproject.toml
├── requirements.txt
├── README.md
└── LICENSE
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details. 