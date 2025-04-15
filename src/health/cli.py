#!/usr/bin/env python3

import click

@click.group()
def cli():
    """Team Health Reporter - A CLI tool for reporting team health metrics."""
    pass

@cli.command()
def report():
    """Generate a team health report."""
    click.echo("Generating team health report...")

if __name__ == "__main__":
    cli() 