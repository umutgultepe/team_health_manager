from setuptools import setup, find_packages

setup(
    name="team-health-reporter",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "click>=8.0.0",
        "pytest>=7.0.0",
        "pytest-cov>=4.0.0",
        "requests>=2.31.0",
        "PyYAML>=6.0.1",
        "slack-sdk>=3.27.0",
    ],
    entry_points={
        "console_scripts": [
            "health=health.cli.base:cli",
        ],
    },
    python_requires=">=3.8",
) 