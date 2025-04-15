from click.testing import CliRunner
from health.cli import cli

def test_cli():
    runner = CliRunner()
    result = runner.invoke(cli)
    assert result.exit_code == 0
    assert "Team Health Reporter" in result.output

def test_report_command():
    runner = CliRunner()
    result = runner.invoke(cli, ["report"])
    assert result.exit_code == 0
    assert "Generating team health report" in result.output 