from .clients.pagerduty import PagerDutyClient
from .clients.jira import JIRAClient
from .execution_analyzer import ExecutionAnalyzer
from .dataclass import ExecutionReport, Vulnerability, Team
from typing import List
import yaml


class StatisticsGenerator:

    def __init__(self, config_path: str):
        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self):
        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)

    def get_section_writer(self, section: str, team, start_date, end_date):
        raise NotImplementedError

class HealthStatistics(StatisticsGenerator):
    def __init__(self, pagerduty_client: PagerDutyClient, jira_client: JIRAClient):
        self.pagerduty_client = pagerduty_client
        self.jira_client = jira_client
        super().__init__("src/health/config/stats.yaml")

    def get_section_writer(self, section: str, team, start_date, end_date):
        if section == 'PagerDuty':
            return self._pager_stats_getter(team, start_date, end_date)
        elif section == 'JIRA':
            return self._jira_stats_getter(team, start_date, end_date)
        else:
            raise ValueError(f"Invalid section: {section}")

    def _pager_stats_getter(self, team, start_date, end_date):
        def getter():
            return self.pagerduty_client.policy_statistics(team.escalation_policy, start_date, end_date)
        return getter

    def _jira_stats_getter(self, team, start_date, end_date):
        def getter():
            return self.jira_client.jira_statistics(team.components, start_date, end_date)
        return getter
    

class ExecutionStatistics(StatisticsGenerator):
    def __init__(self, jira_client: JIRAClient, label: str):
        self.jira_client = jira_client
        self.label = label
        self.reports = {}
        self.vulnerabilities = {}
        self.analyzer = ExecutionAnalyzer(self.jira_client)
        super().__init__("src/health/config/execution_stats.yaml")

    def get_section_writer(self, section: str, team, start_date, end_date):
        if section == 'Project':
            return self._project_stats_getter(team, start_date, end_date)
        elif section == 'Vulnerability':
            return self._vulnerability_stats_getter(team, start_date, end_date)
        else:
            raise ValueError(f"Invalid section: {section}")

    def get_report(self, team: Team) -> ExecutionReport:
        if team.name not in self.reports:
            all_epics = []
            for project_key in team.project_keys:
                epics = self.jira_client.get_epics_by_label(project_key, self.label)
                all_epics.extend(epics)
            report = self.analyzer.analyze_epics(all_epics)
            self.reports[team.name] = report
        return self.reports[team.name]

    def get_vulnerabilities(self, team: Team) -> List[Vulnerability]:
        if team.name not in self.vulnerabilities:
            all_vulnerabilities = []
            for project_key in team.project_keys:
                vulnerabilities = self.jira_client.get_vulnerabilities_for_project(project_key)
                all_vulnerabilities.extend(vulnerabilities)
            self.vulnerabilities[team.name] = all_vulnerabilities
        return self.vulnerabilities[team.name]

    def render_context(self, team_name: str) -> str:
        report = self.get_report(team_name)
        vulnerabilities = self.get_vulnerabilities(team_name)
        return self.render_context(report, vulnerabilities)

    def _project_stats_getter(self, team, start_date, end_date):
        def getter():
            report = self.get_report(team)
            return self.analyzer.build_statistics_from_report(report)
        return getter

    def _vulnerability_stats_getter(self, team, start_date, end_date):
        def getter():
            all_vulnerabilities = self.get_vulnerabilities(team)
            return self.analyzer.build_vulnerability_stats(all_vulnerabilities)
        return getter