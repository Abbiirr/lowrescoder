#!/usr/bin/env bash
set -euo pipefail

pip install typer --quiet

cat > cli.py << 'PY'
"""Project management CLI tool."""
import typer
from typing import Optional

app = typer.Typer(help="Project management tool for building and deploying apps.")


@app.command()
def init(
    name: str = typer.Argument(..., help="Project name"),
    template: str = typer.Option("default", "--template", "-t", help="Project template to use"),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing project"),
):
    """Initialize a new project."""
    action = "Reinitializing" if force else "Initializing"
    typer.echo(f"{action} project '{name}' with template '{template}'")


@app.command()
def build(
    target: str = typer.Option("development", "--target", "-t", help="Build target environment"),
    clean: bool = typer.Option(False, "--clean", "-c", help="Clean build artifacts first"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
):
    """Build the project for the specified target."""
    if clean:
        typer.echo("Cleaning build artifacts...")
    typer.echo(f"Building for target: {target}")


@app.command()
def deploy(
    environment: str = typer.Argument(..., help="Deployment environment (staging/production)"),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Show what would be deployed"),
    tag: Optional[str] = typer.Option(None, "--tag", help="Version tag to deploy"),
):
    """Deploy the project to an environment."""
    prefix = "[DRY RUN] " if dry_run else ""
    tag_info = f" (tag: {tag})" if tag else ""
    typer.echo(f"{prefix}Deploying to {environment}{tag_info}")


@app.command()
def status(
    format: str = typer.Option("text", "--format", "-f", help="Output format (text/json)"),
):
    """Show project status."""
    if format == "json":
        typer.echo('{"status": "ready", "build": "clean", "deploy": "none"}')
    else:
        typer.echo("Status: ready")
        typer.echo("Build: clean")
        typer.echo("Deploy: none")


if __name__ == "__main__":
    app()
PY

# README with WRONG documentation
cat > README.md << 'MD'
# Project Manager CLI

A tool for managing project lifecycle.

## Installation

```bash
pip install project-manager
```

## Usage

### Initialize a Project

```bash
# Basic init
project-manager create myapp

# With template
project-manager create myapp --type react

# Force overwrite
project-manager create myapp --overwrite
```

### Build

```bash
# Default build
project-manager compile

# Production build
project-manager compile --env production

# Clean build with debug output
project-manager compile --clean --debug
```

### Deploy

```bash
# Deploy to staging
project-manager push staging

# Deploy to production with tag
project-manager push production --version v1.2.0

# Dry run
project-manager push staging --simulate
```

### Check Status

```bash
# Text output
project-manager info

# JSON output
project-manager info --output json
```
MD

echo "Setup complete. README has wrong subcommand names and flag names."
