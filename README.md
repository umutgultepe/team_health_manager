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

After installation and configuration, you can use the following commands:

### Slack Commands

```bash
# Get messages from a Slack channel
health get-slack-messages <channel> [--start START] [--end END] [--raw]

Options:
  --start    Start time in UTC (YYYY-MM-DD HH:MM:SS)
  --end      End time in UTC (YYYY-MM-DD HH:MM:SS)
  --raw      Show raw message data
```

### PagerDuty Commands

```bash
# List incidents for a team
health list-incidents-for-team <team_key> [--start START] [--end END] [--config CONFIG] [--raw]

# Get pager statistics for a team
health pager-stats <team_key> [--start START] [--end END] [--config CONFIG]

# Get details of a specific incident
health describe-incident <incident_id> [--raw]

Options:
  --start    Start time in UTC (YYYY-MM-DD HH:MM:SS)
  --end      End time in UTC (YYYY-MM-DD HH:MM:SS)
  --config   Path to team configuration file (default: src/health/config/team.yaml)
  --raw      Show raw incident data and logs
```

### JIRA Commands

```bash
# List ARN project issues for a component
health list-arns <component> [--start START] [--end END]

# List ARN project issues for a team
health team-arns <team_key> [--start START] [--end END] [--config CONFIG]

# Get ARN counts across teams
health arn-counts [--start START] [--end END] [--config CONFIG]

Options:
  --start    Start time in UTC (YYYY-MM-DD HH:MM:SS)
  --end      End time in UTC (YYYY-MM-DD HH:MM:SS)
  --config   Path to team configuration file (default: src/health/config/team.yaml)
```

### General Options

- All time-based commands use UTC timezone
- If `--start` and `--end` are not specified, the default time range is used (Monday 00:00 to Sunday 23:59 UTC of the most recent complete week)
- Use `--help` with any command to see its specific options and usage

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