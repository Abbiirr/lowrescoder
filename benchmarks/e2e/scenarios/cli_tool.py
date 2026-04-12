"""E2E-CLI scenario: Build a CLI tool with argument parsing and config.

The agent must create a Node.js CLI tool with:
- Argument parsing (commander or yargs)
- Config file support (JSON/YAML)
- Help/version output
- Basic smoke tests

Scoring focuses on:
- Functionality: CLI works as specified
- Error handling: invalid inputs handled gracefully
- Testing: smoke tests pass
- Code quality: proper structure and organization
"""

from __future__ import annotations

from e2e.scenario_contract import AcceptanceCheck, ScenarioManifest

SCENARIO_ID = "E2E-CLI"

MANIFEST = ScenarioManifest(
    scenario_id=SCENARIO_ID,
    name="CLI Tool Benchmark",
    description=(
        "Build a Node.js CLI tool that processes text files. "
        "The tool should support argument parsing, config files, "
        "and include basic tests."
    ),
    prompt=(
        "Create a Node.js CLI tool called 'textool' that processes text files. "
        "Features:\n"
        "1. `textool count <file>` — count lines, words, characters\n"
        "2. `textool search <pattern> <file>` — grep-like search with line numbers\n"
        "3. `textool stats <file>` — show file statistics (size, encoding, line endings)\n"
        "4. `--format json|table` flag for output format\n"
        "5. `--config <path>` flag to load defaults from a JSON config file\n"
        "6. `--help` and `--version` flags\n\n"
        "Use commander for arg parsing. Include Jest tests for each command. "
        "All files in the current directory (.), not a subdirectory."
    ),
    follow_ups=[
        "Ensure all tests pass with `npm test`. Fix any issues.",
        "Make sure `node index.js --help` and `node index.js --version` work.",
    ],
    expected_files=["package.json", "index.js"],
    expected_commands=["npm test", "node index.js --help"],
    acceptance_checks=[
        AcceptanceCheck(
            name="tests_pass",
            command="npm test",
            timeout_s=60,
            required=True,
        ),
        AcceptanceCheck(
            name="help_works",
            command="node index.js --help",
            timeout_s=10,
            required=True,
        ),
        AcceptanceCheck(
            name="version_works",
            command="node index.js --version",
            timeout_s=10,
            required=False,
        ),
    ],
    max_score=100,
    scoring_categories={
        "functionality": 40,
        "error_handling": 20,
        "testing": 25,
        "code_quality": 15,
    },
    max_wall_time_s=900,
    max_tool_calls=75,
    max_turns=4,
    min_score=40,
    strict_min_score=70,
    language="javascript",
    tags=["cli", "deterministic", "regression-lane"],
    setup_commands=[],
    required_artifacts=["package.json", "index.js"],
)
