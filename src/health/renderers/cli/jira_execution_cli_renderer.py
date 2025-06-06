"""
JIRA Execution CLI Renderer for Team Health Manager.

This module contains the CLI renderer specifically for JIRA execution reports,
including hierarchical Epic → Stories display and watch mode functionality.
"""

import click
import os
from datetime import datetime
from typing import Dict, List
from .base import CliRenderer
from ...dataclass import IssueStatus


class JiraExecutionCliRenderer(CliRenderer):
    """
    CLI renderer for JIRA execution reports.
    
    Handles hierarchical display of Epic → Stories with beautiful tree structure,
    status emojis, progress tracking, and real-time watch mode functionality.
    """
    
    def render_report(self, report, **kwargs) -> None:
        """
        Render a complete execution report to the console.
        
        Args:
            report: ExecutionReport object containing epics, stories, and problems
            **kwargs: Additional rendering options
        """
        self._print_header("Team Execution Report")
        
        # Print summary
        self._print_summary(report)
        
        # Print status distribution
        if len(report.epics) > 0:
            self._print_status_distribution(report.epics)
        
        # Print problem types summary
        if hasattr(report, 'problems') and len(report.problems) > 0:
            self._print_problem_types(report.problems)
        
        # Always show hierarchical structure
        if len(report.epics) > 0:
            self._print_section("Hierarchical Issue Breakdown", "🌳")
            self._print_separator()
            self._print_hierarchical_issues(report)
        
        self._print_separator()
    
    def render_watch_mode(self, current_report, previous_report, iteration: int, refresh_interval: int) -> None:
        """
        Render the execution report in watch mode with progress tracking.
        
        Args:
            current_report: Current ExecutionReport
            previous_report: Previous ExecutionReport for comparison (can be None)
            iteration: Current iteration number
            refresh_interval: Refresh interval in seconds
        """
        current_time = self._format_timestamp(datetime.now())
        
        click.echo(f"🎯 Team Execution Report - Live Mode (Iteration #{iteration})")
        self._print_separator()
        click.echo(f"🕐 Last Updated: {current_time} | ⏱️  Refresh: {refresh_interval}s")
        
        # Calculate and show progress
        if previous_report:
            self._print_progress_comparison(current_report, previous_report)
        
        # Show current summary with progress indicators
        self._print_watch_summary(current_report, previous_report)
        
        # Show status distribution
        if len(current_report.epics) > 0:
            self._print_status_distribution(current_report.epics)
        
        # Show recently resolved issues
        if previous_report:
            resolved_issues = self._find_resolved_issues(previous_report, current_report)
            if resolved_issues:
                self._print_resolved_issues(resolved_issues)
        
        # Show current issues in abbreviated format
        problem_count = len(current_report.problems) if hasattr(current_report, 'problems') else 0
        if problem_count > 0:
            self._print_section("Current Issues (Hierarchical View)", "🌳")
            self._print_separator()
            self._print_abbreviated_hierarchical_issues(current_report)
        
        self._print_separator()
    
    def _print_summary(self, report):
        """Print the executive summary section."""
        epic_count = len(report.epics)
        story_count = len(report.stories) if hasattr(report, 'stories') and report.stories else 0
        problem_count = len(report.problems) if hasattr(report, 'problems') and report.problems else 0
        
        self._print_section("Summary")
        click.echo(f"   📋 Total Epics: {epic_count}")
        click.echo(f"   📝 Total Stories: {story_count}")
        click.echo(f"   ⚠️  Total Problems: {problem_count}")
    
    def _print_watch_summary(self, current_report, previous_report):
        """Print summary with progress indicators for watch mode."""
        epic_count = len(current_report.epics)
        story_count = len(current_report.stories) if hasattr(current_report, 'stories') and current_report.stories else 0
        problem_count = len(current_report.problems) if hasattr(current_report, 'problems') and current_report.problems else 0
        
        self._print_section("Current Summary")
        click.echo(f"   📋 Total Epics: {epic_count}")
        click.echo(f"   📝 Total Stories: {story_count}")
        
        if previous_report:
            prev_problems = len(previous_report.problems) if hasattr(previous_report, 'problems') else 0
            if problem_count < prev_problems:
                click.echo(f"   ⚠️  Total Problems: {problem_count} ✅ (was {prev_problems}, -{prev_problems - problem_count} resolved!)")
            elif problem_count > prev_problems:
                click.echo(f"   ⚠️  Total Problems: {problem_count} ⚠️ (was {prev_problems}, +{problem_count - prev_problems} new)")
            else:
                click.echo(f"   ⚠️  Total Problems: {problem_count}")
        else:
            click.echo(f"   ⚠️  Total Problems: {problem_count}")
    
    def _print_status_distribution(self, epics):
        """Print the epic status distribution with progress bars."""
        epic_count = len(epics)
        
        # Group epics by status
        status_counts = {}
        for epic in epics:
            status = epic.get_status().value if hasattr(epic, 'get_status') else epic.status
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Status to emoji mapping
        status_emojis = {
            "TODO": "⭕",
            "In Progress": "🔄", 
            "Done": "✅",
            "Invalid": "❌"
        }
        
        self._print_section("Epic Status Distribution", "📈")
        for status, count in status_counts.items():
            percentage = (count / epic_count) * 100
            bar_length = int(percentage / 5)  # Scale to 20 chars max
            bar = "█" * bar_length + "░" * (20 - bar_length)
            emoji = status_emojis.get(status, "❓")
            status_with_emoji = f"{status} ({emoji})"
            click.echo(f"   {status_with_emoji:18} │{bar}│ {count:2d} ({percentage:4.1f}%)")
    
    def _print_problem_types(self, problems):
        """Print the problem types summary."""
        # Group problems by type for summary
        problem_types = {}
        for problem in problems:
            problem_type = problem.problem_type.value if hasattr(problem.problem_type, 'value') else str(problem.problem_type)
            problem_types[problem_type] = problem_types.get(problem_type, 0) + 1
        
        self._print_section("Problem Types", "🔍")
        for problem_type, count in problem_types.items():
            click.echo(f"   • {problem_type}: {count}")
    
    def _print_progress_comparison(self, current_report, previous_report):
        """Print progress comparison between reports."""
        current_problems = len(current_report.problems) if hasattr(current_report, 'problems') else 0
        previous_problems = len(previous_report.problems) if hasattr(previous_report, 'problems') else 0
        problem_change = previous_problems - current_problems
        
        if problem_change > 0:
            click.echo(f"✅ Progress: {problem_change} problems resolved since last check! 🎉")
        elif problem_change < 0:
            click.echo(f"⚠️  Alert: {abs(problem_change)} new problems detected")
        else:
            click.echo(f"📊 Status: No changes since last check")
        click.echo()
    
    def _print_resolved_issues(self, resolved_issues):
        """Print recently resolved issues."""
        self._print_section("Recently Resolved Issues", "🎉")
        for issue_key, problems_resolved in resolved_issues.items():
            click.echo(f"   ✅ {issue_key}: {len(problems_resolved)} problem(s) fixed!")
            for problem in problems_resolved:
                click.echo(f"      • {problem}")
    
    def _print_hierarchical_issues(self, report):
        """Print issues in hierarchical epic -> stories format with full details."""
        # Group problems by issue key for quick lookup
        problems_by_issue = {}
        if hasattr(report, 'problems'):
            for problem in report.problems:
                issue_key = problem.issue.key
                if issue_key not in problems_by_issue:
                    problems_by_issue[issue_key] = []
                problems_by_issue[issue_key].append(problem)
        
        epic_counter = 0
        
        # Process each epic
        for epic in report.epics:
            epic_counter += 1
            problems = problems_by_issue.get(epic.key, [])
            
            # Epic header with status indicator
            status_emoji = self._get_status_emoji(epic.get_status())
            assignee_display = f"👤 {epic.assignee}" if epic.assignee != "Unassigned" else "👤 Unassigned"
            
            click.echo(f"\n🎯 EPIC #{epic_counter:02d} {status_emoji}")
            click.echo(f"┌─ {epic.key} │ {assignee_display}")
            click.echo(f"│  📋 {epic.summary}")
            click.echo(f"│  🔗 https://abnormalsecurity.atlassian.net/browse/{epic.key}")
            
            if epic.start_date:
                click.echo(f"│  📅 Start: {epic.start_date.strftime('%Y-%m-%d')}")
            if epic.due_date:
                click.echo(f"│  ⏰ Due: {epic.due_date.strftime('%Y-%m-%d')}")
            
            # Show epic problems
            if problems:
                click.echo(f"│")
                click.echo(f"│  ⚠️  Issues with this epic:")
                for problem in problems:
                    clean_description = self._clean_problem_description(problem.description, epic.key, "Epic")
                    click.echo(f"│     • {clean_description}")
            else:
                # Show when epic is clean
                click.echo(f"│")
                click.echo(f"│  ✅ Epic looks good - no issues detected!")
            
            # Fetch and show stories for this epic
            epic_stories = self._get_stories_for_epic(epic.key)
            
            # Always show stories section
            click.echo(f"│")
            if epic_stories:
                click.echo(f"│  📝 Stories ({len(epic_stories)}):")
                
                for i, story in enumerate(epic_stories):
                    story_problems = problems_by_issue.get(story.key, [])
                    is_last_story = (i == len(epic_stories) - 1)
                    
                    story_status_emoji = self._get_status_emoji(story.get_status())
                    story_assignee = f"👤 {story.assignee}" if story.assignee != "Unassigned" else "👤 Unassigned"
                    
                    prefix = "└─" if is_last_story else "├─"
                    continuation = "   " if is_last_story else "│  "
                    
                    click.echo(f"│  {prefix} {story_status_emoji} {story.key} │ {story_assignee}")
                    click.echo(f"│  {continuation}   📋 {story.summary}")
                    click.echo(f"│  {continuation}   🔗 https://abnormalsecurity.atlassian.net/browse/{story.key}")
                    
                    if story_problems:
                        click.echo(f"│  {continuation}   ⚠️  Issues:")
                        for problem in story_problems:
                            clean_description = self._clean_problem_description(problem.description, story.key, "Story")
                            click.echo(f"│  {continuation}      • {clean_description}")
                    else:
                        click.echo(f"│  {continuation}   ✅ Story looks good!")
                    
                    if not is_last_story:
                        click.echo(f"│  │")
            else:
                click.echo(f"│  📝 Stories: No stories found for this epic")
            
            click.echo(f"└{'─' * 78}")
    
    def _print_abbreviated_hierarchical_issues(self, report):
        """Print a condensed version of hierarchical issues for watch mode."""
        # Group problems by issue key for quick lookup
        problems_by_issue = {}
        if hasattr(report, 'problems'):
            for problem in report.problems:
                issue_key = problem.issue.key
                if issue_key not in problems_by_issue:
                    problems_by_issue[issue_key] = []
                problems_by_issue[issue_key].append(problem)
        
        # Show only epics with problems for brevity
        epics_with_problems = [epic for epic in report.epics if epic.key in problems_by_issue]
        
        if not epics_with_problems:
            click.echo("🎉 No epics have outstanding problems!")
            return
        
        # Show ALL epics with problems in hierarchical format
        for epic in epics_with_problems:
            epic_problems = problems_by_issue.get(epic.key, [])
            status_emoji = self._get_status_emoji(epic.get_status())
            
            # Epic header
            click.echo(f"🎯 {epic.key} {status_emoji} │ 👤 {epic.assignee} │ {len(epic_problems)} epic issue(s)")
            click.echo(f"┌─ 📋 {epic.summary}")
            
            # Show epic problems
            for problem in epic_problems[:2]:  # Limit to 2 for compactness
                clean_desc = self._clean_problem_description(problem.description, epic.key, "Epic")
                click.echo(f"│  ⚠️  {clean_desc}")
            
            if len(epic_problems) > 2:
                click.echo(f"│  ... and {len(epic_problems) - 2} more epic problem(s)")
            
            # Fetch and show stories for this epic
            try:
                epic_stories = self._get_stories_for_epic(epic.key)
                stories_with_problems = [s for s in epic_stories if s.key in problems_by_issue]
                
                if stories_with_problems:
                    click.echo(f"│")
                    click.echo(f"│  📝 Stories with problems ({len(stories_with_problems)}):")
                    
                    for i, story in enumerate(stories_with_problems):
                        story_problems = problems_by_issue.get(story.key, [])
                        story_status_emoji = self._get_status_emoji(story.get_status())
                        is_last_story = (i == len(stories_with_problems) - 1)
                        
                        prefix = "└─" if is_last_story else "├─"
                        continuation = "   " if is_last_story else "│  "
                        
                        click.echo(f"│  {prefix} {story_status_emoji} {story.key} │ 👤 {story.assignee} │ {len(story_problems)} issue(s)")
                        click.echo(f"│  {continuation}   📋 {story.summary}")
                        
                        # Show first 2 story problems
                        for problem in story_problems[:2]:
                            clean_desc = self._clean_problem_description(problem.description, story.key, "Story")
                            click.echo(f"│  {continuation}   ⚠️  {clean_desc}")
                        
                        if len(story_problems) > 2:
                            click.echo(f"│  {continuation}   ... and {len(story_problems) - 2} more")
                        
                        if not is_last_story:
                            click.echo(f"│  │")
                else:
                    # Check if epic has stories at all
                    if epic_stories:
                        click.echo(f"│")
                        click.echo(f"│  📝 Stories ({len(epic_stories)}): All stories look good! ✅")
                    else:
                        if epic.get_status().value == "In Progress":
                            click.echo(f"│")
                            click.echo(f"│  📝 Stories: None (This may be why there's an issue!)")
            
            except Exception:
                # If we can't fetch stories, just note it
                click.echo(f"│  📝 Stories: Unable to fetch (continuing...)")
            
            click.echo(f"└{'─' * 70}")
            click.echo()  # Blank line between epics
    
    def _get_status_emoji(self, status: IssueStatus) -> str:
        """Get emoji representation for issue status."""
        status_emojis = {
            IssueStatus.TODO: "⭕",        # To Do
            IssueStatus.IN_PROGRESS: "🔄", # In Progress  
            IssueStatus.DONE: "✅",        # Done
            IssueStatus.INVALID: "❌"      # Invalid
        }
        return status_emojis.get(status, "❓")
    
    def _clean_problem_description(self, description: str, issue_key: str, issue_type: str) -> str:
        """Clean up problem description by removing redundant issue references."""
        clean_description = description.replace(f"{issue_type} {issue_key} ", "").replace(f"Story {issue_key} ", "")
        
        # Standardize capitalization
        if clean_description.startswith("is in"):
            clean_description = "Is in" + clean_description[5:]
        elif clean_description.startswith("has no"):
            clean_description = "Has no" + clean_description[6:]
        
        return clean_description
    
    def _get_stories_for_epic(self, epic_key: str):
        """Get stories for a specific epic using JIRA client."""
        try:
            from ...clients.jira import JIRAClient
            jira_client = JIRAClient()
            return jira_client.get_stories_by_epic(epic_key)
        except Exception:
            return []
    
    def _find_resolved_issues(self, previous_report, current_report):
        """Find issues that had problems resolved between reports."""
        # Create problem sets for comparison
        previous_problems = set()
        current_problems = set()
        
        if hasattr(previous_report, 'problems'):
            previous_problems = {(p.issue.key, p.description) for p in previous_report.problems}
        
        if hasattr(current_report, 'problems'):
            current_problems = {(p.issue.key, p.description) for p in current_report.problems}
        
        # Find resolved problems
        resolved_problems = previous_problems - current_problems
        
        # Group by issue key
        resolved_by_issue = {}
        for issue_key, description in resolved_problems:
            if issue_key not in resolved_by_issue:
                resolved_by_issue[issue_key] = []
            resolved_by_issue[issue_key].append(description)
        
        return resolved_by_issue 