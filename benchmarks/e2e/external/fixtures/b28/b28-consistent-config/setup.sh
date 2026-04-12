#!/usr/bin/env bash
set -euo pipefail

mkdir -p project

cat > project/config_a.json << 'EOF'
{
  "app": {
    "name": "MyApp",
    "version": "1.0.0",
    "debug": false
  },
  "database": {
    "host": "localhost",
    "port": 5432,
    "name": "myapp_db"
  },
  "logging": {
    "level": "INFO",
    "format": "text"
  },
  "feature_flags": {
    "dark_mode": false,
    "beta_api": false
  }
}
EOF

cat > project/config_b.json << 'EOF'
{
  "app": {
    "version": "2.0.0",
    "debug": true,
    "author": "Team B"
  },
  "database": {
    "host": "db.example.com",
    "pool_size": 10
  },
  "cache": {
    "backend": "redis",
    "ttl": 3600
  },
  "feature_flags": {
    "dark_mode": true,
    "new_ui": true
  }
}
EOF

cat > project/config_c.json << 'EOF'
{
  "app": {
    "version": "2.1.0",
    "environment": "production"
  },
  "database": {
    "port": 5433,
    "ssl": true
  },
  "logging": {
    "level": "WARNING",
    "file": "/var/log/app.log"
  },
  "cache": {
    "ttl": 7200,
    "max_entries": 10000
  }
}
EOF

# Expected merge result:
# - Conflict resolution: alphabetically-last filename wins
# - config_c.json > config_b.json > config_a.json for conflicts
# - Nested objects are deep-merged
cat > project/expected_merged.json << 'EOF'
{
  "app": {
    "author": "Team B",
    "debug": true,
    "environment": "production",
    "name": "MyApp",
    "version": "2.1.0"
  },
  "cache": {
    "backend": "redis",
    "max_entries": 10000,
    "ttl": 7200
  },
  "database": {
    "host": "db.example.com",
    "name": "myapp_db",
    "pool_size": 10,
    "port": 5433,
    "ssl": true
  },
  "feature_flags": {
    "beta_api": false,
    "dark_mode": true,
    "new_ui": true
  },
  "logging": {
    "file": "/var/log/app.log",
    "format": "text",
    "level": "WARNING"
  }
}
EOF

cat > project/merger.py << 'PYEOF'
"""Config merger — merges multiple JSON config files deterministically."""
import json
import os


def merge_configs(config_paths):
    """Merge multiple JSON config files into one.

    Conflict resolution: when keys conflict at any level, the value from
    the file whose filename comes last alphabetically wins.

    Nested objects are deep-merged (not replaced wholesale).

    The output keys are sorted alphabetically at every level for consistency.

    Args:
        config_paths: List of paths to JSON config files.

    Returns:
        dict: Merged configuration.
    """
    # TODO: Implement deterministic config merging
    pass


def merge_to_file(config_paths, output_path):
    """Merge configs and write to file.

    Args:
        config_paths: List of paths to JSON config files.
        output_path: Path to write merged JSON.
    """
    merged = merge_configs(config_paths)
    with open(output_path, 'w') as f:
        json.dump(merged, f, indent=2, sort_keys=True)
PYEOF

cat > project/test_merger.py << 'PYEOF'
"""Tests for the config merger."""
import unittest
import json
import os
import itertools
from merger import merge_configs


class TestMerger(unittest.TestCase):

    def setUp(self):
        base = os.path.dirname(__file__)
        self.paths = [
            os.path.join(base, "config_a.json"),
            os.path.join(base, "config_b.json"),
            os.path.join(base, "config_c.json"),
        ]
        with open(os.path.join(base, "expected_merged.json")) as f:
            self.expected = json.load(f)

    def test_merge_matches_expected(self):
        result = merge_configs(self.paths)
        self.assertEqual(result, self.expected)

    def test_order_independent(self):
        """All 6 permutations of input order produce identical output."""
        results = []
        for perm in itertools.permutations(self.paths):
            result = merge_configs(list(perm))
            results.append(json.dumps(result, sort_keys=True))
        self.assertTrue(all(r == results[0] for r in results),
                        "Output differs for different input orders")

    def test_deep_merge(self):
        """Nested objects should be deep-merged, not replaced."""
        result = merge_configs(self.paths)
        # database should have keys from all 3 configs
        db = result["database"]
        self.assertIn("host", db)       # from config_a (overridden by config_b)
        self.assertIn("port", db)       # from config_a (overridden by config_c)
        self.assertIn("name", db)       # only in config_a
        self.assertIn("pool_size", db)  # only in config_b
        self.assertIn("ssl", db)        # only in config_c

    def test_conflict_resolution(self):
        """Alphabetically-last file wins for conflicting keys."""
        result = merge_configs(self.paths)
        # version: config_a=1.0.0, config_b=2.0.0, config_c=2.1.0
        # config_c wins (alphabetically last)
        self.assertEqual(result["app"]["version"], "2.1.0")
        # debug: config_a=false, config_b=true
        # config_b wins (config_c doesn't have it)
        self.assertEqual(result["app"]["debug"], True)

    def test_unique_keys_preserved(self):
        """Keys that only appear in one config should be preserved."""
        result = merge_configs(self.paths)
        self.assertEqual(result["app"]["name"], "MyApp")  # only in config_a
        self.assertEqual(result["app"]["author"], "Team B")  # only in config_b
        self.assertEqual(result["app"]["environment"], "production")  # only in config_c

    def test_returns_dict(self):
        result = merge_configs(self.paths)
        self.assertIsInstance(result, dict)

    def test_sorted_keys(self):
        """Output keys should be sorted at every level."""
        result = merge_configs(self.paths)
        self.assertEqual(list(result.keys()), sorted(result.keys()))
        for key in result:
            if isinstance(result[key], dict):
                self.assertEqual(list(result[key].keys()),
                                 sorted(result[key].keys()))


if __name__ == "__main__":
    unittest.main()
PYEOF

echo "Setup complete. merger.py needs merge_configs() implemented."
