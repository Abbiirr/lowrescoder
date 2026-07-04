#!/usr/bin/env bash
# Setup for tb-010-conda-env-conflict-resolution
# Creates a requirements.txt with conflicting version constraints
# and a stub resolver script. No actual conda needed — this is a
# constraint-solving task using pip-compatible version specifiers.
set -euo pipefail

# Create the conflicting requirements file
cat > requirements_broken.txt << 'REQS'
# Project dependencies — BROKEN: has conflicts
# The agent must produce a working requirements_fixed.txt

# Web framework
flask>=2.0,<3.0
werkzeug>=2.0

# Database
sqlalchemy>=1.4,<2.0
sqlalchemy>=2.0,<3.0

# HTTP client
requests>=2.28
urllib3>=1.26,<2.0
urllib3>=2.0

# Data processing
pandas>=1.5
numpy>=1.24,<1.25
numpy>=1.25

# Testing
pytest>=7.0
pytest<7.0
REQS

# Create a package version database (simulated)
cat > .package_versions.json << 'VERSIONS'
{
  "flask": ["2.0.0", "2.1.0", "2.2.0", "2.3.0"],
  "werkzeug": ["2.0.0", "2.1.0", "2.2.0", "2.3.0", "3.0.0"],
  "sqlalchemy": ["1.4.0", "1.4.50", "2.0.0", "2.0.25"],
  "requests": ["2.28.0", "2.28.2", "2.31.0"],
  "urllib3": ["1.26.0", "1.26.18", "2.0.0", "2.1.0"],
  "pandas": ["1.5.0", "1.5.3", "2.0.0", "2.1.0"],
  "numpy": ["1.24.0", "1.24.4", "1.25.0", "1.25.2", "1.26.0"],
  "pytest": ["6.2.0", "7.0.0", "7.4.0", "8.0.0"]
}
VERSIONS

# Create stub resolver
cat > resolve.py << 'STUB'
#!/usr/bin/env python3
"""Resolve dependency conflicts in requirements_broken.txt.

The file has conflicting version constraints:
1. sqlalchemy has two mutually exclusive version ranges
2. urllib3 has two mutually exclusive version ranges
3. numpy has two mutually exclusive version ranges
4. pytest has contradictory constraints (>=7.0 AND <7.0)

Task:
- Read requirements_broken.txt
- Identify and resolve all conflicts by choosing ONE valid version range
  for each conflicting package
- Write requirements_fixed.txt with resolved, non-conflicting constraints
- Each package should appear exactly ONCE
- Keep non-conflicting packages as-is
- Write conflict_report.txt explaining what conflicts were found and how
  they were resolved

Resolution strategy: prefer the NEWER version range when there's a conflict.
"""
# TODO: Implement conflict resolution
STUB

chmod +x resolve.py

echo "Setup complete. requirements_broken.txt created with conflicts."
