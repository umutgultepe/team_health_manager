# Team Health Reporter

A comprehensive CLI tool for reporting team health metrics and execution analysis, designed to help teams track and analyze their health metrics, project execution, and performance over time.

## Features

- **Automated Health Metric Reporting**: Collect and report on PagerDuty incidents, JIRA issues, and team performance metrics
- **Execution Analysis**: AI-powered analysis of epic updates, project execution tracking, and vulnerability management
- **Google Integration**: Seamless integration with Google Sheets, Google Drive, and Google Docs for data storage and reporting
- **Slack Integration**: Fetch messages and notifications from Slack channels
- **AI-Powered Insights**: ChatGPT integration for intelligent analysis and scoring of team updates
- **Comprehensive Statistics**: Detailed metrics for PagerDuty, JIRA, and project execution
- **Retry Mechanism**: Robust API rate limit handling with automatic retries
- **Configurable**: Flexible configuration through YAML files for teams, statistics, and execution metrics

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

1. **Google API Setup**:
   - Create a service account in Google Cloud Console
   - Enable Google Sheets, Google Drive, and Google Docs APIs
   - Download the credentials JSON file
   - Place it as `src/health/config/google_credentials.json`

2. **Slack Integration**:
   - Create a Slack app
   - Get the bot token
   - Add it to your configuration

3. **JIRA Integration**:
   - Configure JIRA API credentials
   - Set up project keys and components for teams

4. **PagerDuty Integration**:
   - Set up PagerDuty API access
   - Configure escalation policies for teams

5. **AI Integration**:
   - Set up Google Generative AI API access for ChatGPT integration

6. **Update Configuration Files**:
   - `src/health/config/credentials.py` for API keys and tokens
   - `src/health/config/team.yaml` for team configurations
   - `src/health/config/stats.yaml` for health statistics configuration
   - `src/health/config/execution_stats.yaml` for execution metrics configuration

## Usage

After installation and configuration, you can use the following commands:

### AI Commands

```bash
# Call ChatGPT API with a custom prompt
health ai <prompt>

Example:
health ai "Analyze the current sprint progress for team Alpha"
```

### Execution Analysis Commands

```bash
# Evaluate an epic update using AI scoring
health evaluate-epic-update <epic_key>

# Generate team execution report
health team-execution-report <team_key> <label>

# Get epic updates for a team
health epic-updates <team_key> <label>

# List vulnerabilities for a team
health list-vulnerabilities <team_key>

# Refresh execution data for a team
health refresh-execution-for-team <team_key> <label>

# Refresh execution data for all teams
health refresh-all-execution <label> [--skip-teams team1,team2]

# Write execution report for a team
health write-report-for-team <team_key>

# Write execution headers for a team
health write-execution-headers <team_key>

# Write execution statistics for a team
health write-execution-stats <team_key> <label> [--section SECTION]

# Render report context for a team
health render-report-context <team_key> <label>

# Render report from context file
health render-from-context <context_file_path>
```

### Statistics Commands

```bash
# Write headers for team statistics
health write-headers <team_key>

# Write statistics for a team
health write-stats <team_key> [--section SECTION]

# Overwrite specific statistics
health overwrite <section> <header> [--team-key TEAM_KEY]

# Fill date ranges in Google Sheets
health fill-dates [team_key]

# Refresh all team statistics
health refresh-all [--skip-date-fill]
```

### Google Integration Commands

```bash
# Write text to a specific cell in Google Sheets
health fill-cell <tab_name> <coordinate> <text>

# Write a local file to Google Drive
health write-file <local_path> <remote_path>

# Read a file from Google Drive
health read-file <remote_path>

# Write content to Google Docs tab
health write-to-docs <tab_name> <filename>
```

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

# List epics for a project with a specific label
health list-epics <project_key> <label>

# List stories for an epic
health list-stories <epic_key>

Options:
  --start    Start time in UTC (YYYY-MM-DD HH:MM:SS)
  --end      End time in UTC (YYYY-MM-DD HH:MM:SS)
  --config   Path to team configuration file (default: src/health/config/team.yaml)
```

### General Options

- All time-based commands use UTC timezone
- If `--start` and `--end` are not specified, the default time range is used (Monday 00:00 to Sunday 23:59 UTC of the most recent complete week)
- Use `--help` with any command to see its specific options and usage

## Configuration Files

### Team Configuration (`src/health/config/team.yaml`)

```yaml
team_key:
  name: "Team Name"
  help_channel: "#slack-channel"
  oncall_handle: "@slack-user-group"
  escalation_policy: escalation_policy_id
  project_keys:
    - PRJ
    - PRK
  components:
    - JIRA Component Name
```

### Health Statistics Configuration (`src/health/config/stats.yaml`)

```yaml
PagerDuty:
  total_incidents: Incident Count
  high_urgency_incidents: Incident Count (High Urgency)
  auto_resolved: Auto Resolved 
  timed_out: Missed Response (Escalated)
  mtta_str: Mean Time to Acknowledgment (Minutes)
  total_response_time_str: Total Incident Window (Hours)

JIRA:
  total_arns: ARN Count
```

### Execution Statistics Configuration (`src/health/config/execution_stats.yaml`)

```yaml
Project:
  in_progress_epics: In Progress Epics
  missing_start_date: Missing Start Date
  missing_due_date: Missing Due Date
  past_due_date: Past Due Date
  in_progress_before_start_date: In Progress Before Start Date
  missing_epic_update: Missing Epic Update
  in_progress_epic_without_stories: In Progress Epic Without Stories
  due_date_changed: Due Date Changed

Vulnerability:
  open_vulnerabilities: Open Vulnerabilities
  vulnerabilities_past_due_date: Vulnerabilities Past Due Date
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
│   ├── bin/
│   │   └── health                    # Main CLI entry point
│   └── health/
│       ├── __init__.py
│       ├── cli/                      # CLI command modules
│       │   ├── base.py               # Base CLI setup and utilities
│       │   ├── execution.py          # Execution analysis commands
│       │   ├── google.py             # Google integration commands
│       │   ├── jira.py               # JIRA commands
│       │   ├── pagerduty.py          # PagerDuty commands
│       │   ├── slack.py              # Slack commands
│       │   └── stats.py              # Statistics commands
│       ├── clients/                  # API client modules
│       │   ├── ai.py                 # AI/ChatGPT client
│       │   ├── docs.py               # Google Docs client
│       │   ├── drive.py              # Google Drive client
│       │   ├── jira.py               # JIRA client
│       │   ├── pagerduty.py          # PagerDuty client
│       │   ├── sheets.py             # Google Sheets client
│       │   └── slack.py              # Slack client
│       ├── config/                   # Configuration files
│       │   ├── credentials.py        # API credentials
│       │   ├── team.yaml             # Team configurations
│       │   ├── stats.yaml            # Health statistics config
│       │   ├── execution_stats.yaml  # Execution metrics config
│       │   ├── report_prompt.txt     # AI report prompts
│       │   └── execution_report_template.jinja2  # Report templates
│       ├── dataclass.py              # Data models
│       ├── execution_analyzer.py     # Execution analysis logic
│       ├── statistics_generator.py   # Statistics generation
│       ├── stats_manager.py          # Statistics management
│       └── team_manager.py           # Team management
├── tests/
├── pyproject.toml
├── requirements.txt
├── README.md
└── LICENSE
```

## Key Features Explained

### Execution Analysis
The execution analysis module provides AI-powered insights into project execution:
- **Epic Evaluation**: Uses AI to score and analyze epic updates
- **Project Tracking**: Monitors epics, stories, and project progress
- **Vulnerability Management**: Tracks open vulnerabilities and due dates
- **Problem Detection**: Identifies common project execution issues

### AI Integration
- **ChatGPT Integration**: Direct API access for custom prompts and analysis
- **Intelligent Scoring**: AI-powered evaluation of team updates and progress
- **Automated Insights**: Generate intelligent reports and recommendations

### Google Integration
- **Google Sheets**: Store and manage health metrics and execution data
- **Google Drive**: File storage and retrieval capabilities
- **Google Docs**: Automated report generation and updates

### Comprehensive Statistics
- **PagerDuty Metrics**: Incident counts, response times, escalation tracking
- **JIRA Metrics**: ARN counts, project progress, issue tracking
- **Execution Metrics**: Epic progress, story completion, vulnerability status

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details. 