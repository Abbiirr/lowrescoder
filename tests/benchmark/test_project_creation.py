"""Real-life benchmark: project creation task (React calculator app).

This benchmark scores a generated multi-page calculator web app against a
pragmatic rubric adapted from docs/plan/react-calculator-benchmark.md.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest


def _safe_read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _project_text(project_root: Path) -> str:
    chunks: list[str] = []
    for path in project_root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in {"node_modules", "dist", ".git", ".venv"} for part in path.parts):
            continue
        if path.suffix.lower() in {".js", ".jsx", ".ts", ".tsx", ".json", ".css", ".html"}:
            chunks.append(_safe_read(path))
    return "\n".join(chunks)


def _count_page_files(project_root: Path) -> int:
    if not (project_root / "src").exists():
        return 0
    page_names = ("landing", "home", "regular", "scientific", "currency", "unit", "calculator")
    count = 0
    for path in (project_root / "src").rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".js", ".jsx", ".ts", ".tsx"}:
            continue
        lower = path.name.lower()
        if any(name in lower for name in page_names):
            count += 1
    return count


def _detect_anti_patterns(text: str) -> dict:
    """Detect anti-patterns in raw (non-lowered) project text.

    Returns dict with findings, penalty, critical, and minor categories.
    """
    penalty = 0
    critical: dict[str, int] = {}
    minor: dict[str, int] = {}

    # Critical patterns (-3 each, max -6 per type)
    eval_matches = len(re.findall(r"\beval\s*\(", text))
    func_matches = len(re.findall(r"\bFunction\s*\(", text))
    eval_total = eval_matches + func_matches
    if eval_total > 0:
        critical["eval_usage"] = eval_total
        penalty -= min(eval_total * 3, 6)

    dangerous_html = len(re.findall(r"dangerouslySetInnerHTML", text))
    if dangerous_html > 0:
        critical["dangerous_html"] = dangerous_html
        penalty -= min(dangerous_html * 3, 6)

    # Minor patterns
    todo_count = len(re.findall(r"\b(?:TODO|FIXME)\b", text, re.IGNORECASE))
    if todo_count > 3:
        minor["todo_fixme"] = todo_count
        penalty -= 1

    empty_catch = len(re.findall(r"catch\s*\([^)]*\)\s*\{\s*\}", text))
    if empty_catch > 2:
        minor["empty_catch"] = empty_catch
        penalty -= 1

    console_log = len(re.findall(r"\bconsole\.log\s*\(", text))
    if console_log > 10:
        minor["console_log_spam"] = console_log
        penalty -= 1

    return {
        "findings": {**critical, **minor},
        "penalty": penalty,
        "critical": critical,
        "minor": minor,
    }


def score_react_calculator_project(project_root: Path, run_build: bool = False) -> dict[str, int]:
    """Score a generated calculator project from 0-100.

    Point allocation (100 total):
        scaffold:   15  — project structure, deps, routing
        regular:    10  — basic calculator functionality
        scientific: 15  — trig, log, mathjs integration
        currency:   15  — Frankfurter API, fetch, codes
        unit:       10  — conversion categories and logic
        quality:    10  — code organization, constants, tests
        ui:         25  — dark theme, grid layout, visual polish
    """
    raw_text = _project_text(project_root)
    text = raw_text.lower()
    scores = {
        "scaffold": 0,
        "regular": 0,
        "scientific": 0,
        "currency": 0,
        "unit": 0,
        "quality": 0,
        "ui": 0,
    }

    # --- Scaffold (15 pts) ---
    package_json = project_root / "package.json"
    app_exists = (
        (project_root / "src" / "App.jsx").exists()
        or (project_root / "src" / "App.tsx").exists()
    )
    main_exists = (
        (project_root / "src" / "main.jsx").exists()
        or (project_root / "src" / "main.tsx").exists()
    )
    if package_json.exists() and app_exists and main_exists:
        scores["scaffold"] += 5

    deps_text = _safe_read(package_json).lower()
    required_deps = ["react", "react-dom", "react-router-dom", "mathjs", "big.js"]
    if all(dep in deps_text for dep in required_deps):
        scores["scaffold"] += 5

    if _count_page_files(project_root) >= 5:
        scores["scaffold"] += 3

    if any(token in text for token in ["layout", "<nav", "navbar", "footer"]):
        scores["scaffold"] += 2

    # --- Regular Calculator (10 pts) ---
    if all(op in text for op in ["+", "-", "*", "/"]):
        scores["regular"] += 4
    if any(token in text for token in ["clear", "backspace", "ac"]):
        scores["regular"] += 3
    if any(token in text for token in ["divide by zero", "infinity", "error"]):
        scores["regular"] += 3

    # --- Scientific Calculator (15 pts) ---
    if "mathjs" in text:
        scores["scientific"] += 4
    if all(fn in text for fn in ["sin", "cos", "tan"]):
        scores["scientific"] += 4
    if any(fn in text for fn in ["log", "ln", "sqrt", "pow", "factorial"]):
        scores["scientific"] += 4
    if any(token in text for token in ["degree", "radian"]):
        scores["scientific"] += 3

    # --- Currency Converter (15 pts) ---
    if "frankfurter" in text:
        scores["currency"] += 5
    if any(token in text for token in ["fetch(", "axios", "await fetch", "loading", "error"]):
        scores["currency"] += 4
    currency_codes = {"usd", "eur", "gbp", "jpy", "cad", "aud", "chf", "cny", "inr", "mxn"}
    if sum(1 for code in currency_codes if code in text) >= 10:
        scores["currency"] += 3
    if any(
        token in text
        for token in ["swap", "fromcurrency", "tocurrency", "from currency", "to currency"]
    ):
        scores["currency"] += 2
    if any(token in text for token in ["cache", "localstorage", "memo"]):
        scores["currency"] += 1

    # --- Unit Converter (10 pts) ---
    unit_signals = ["length", "weight", "temperature", "volume", "speed"]
    if sum(1 for token in unit_signals if token in text) >= 3:
        scores["unit"] += 4
    if all(token in text for token in ["mile", "km", "kg", "lbs", "c", "f"]):
        scores["unit"] += 3
    if any(token in text for token in ["fromunit", "tounit", "from unit", "to unit"]):
        scores["unit"] += 2
    if "kelvin" in text or "273.15" in text:
        scores["unit"] += 1

    # --- Code Quality (10 pts) ---
    if (project_root / "src" / "hooks").exists():
        scores["quality"] += 3
    if any(token in text for token in ["constants", "conversionfactors", "conversion_factors"]):
        scores["quality"] += 3
    if any(
        (project_root / name).exists()
        for name in ("tests", "__tests__", "playwright.config.js", "vitest.config.ts")
    ):
        scores["quality"] += 2
    if "todo" not in text and "fixme" not in text:
        scores["quality"] += 2

    # --- UI Quality (25 pts) ---

    # Dark theme (5 pts): dark backgrounds + light text
    dark_bg_tokens = [
        "bg-gray-800", "bg-gray-900", "bg-slate-800", "bg-slate-900",
        "bg-zinc-800", "bg-zinc-900", "bg-neutral-800", "bg-neutral-900",
    ]
    if sum(1 for t in dark_bg_tokens if t in text) >= 2:
        scores["ui"] += 3
    light_text_tokens = ["text-white", "text-gray-100", "text-gray-200", "text-slate-100"]
    if any(t in text for t in light_text_tokens):
        scores["ui"] += 2

    # Grid button layout (5 pts): CSS grid for calculator buttons
    grid_tokens = ["grid-cols-4", "grid-cols-3", "grid cols-4"]
    if any(t in text for t in grid_tokens):
        scores["ui"] += 3
    if "gap-" in text:
        scores["ui"] += 2

    # Color-coded buttons (4 pts): accent colors for operators/equals
    accent_tokens = [
        "bg-orange-", "bg-indigo-", "bg-blue-", "bg-purple-",
        "bg-amber-", "bg-yellow-", "bg-green-", "bg-red-",
    ]
    if sum(1 for t in accent_tokens if t in text) >= 2:
        scores["ui"] += 4

    # Rounded corners + shadows (3 pts): visual depth
    if any(t in text for t in ["rounded-xl", "rounded-2xl", "rounded-lg"]):
        scores["ui"] += 2
    if any(t in text for t in ["shadow-lg", "shadow-xl", "shadow-md"]):
        scores["ui"] += 1

    # Large display text (3 pts): prominent result display
    large_text = ["text-4xl", "text-5xl", "text-3xl", "text-6xl"]
    if any(t in text for t in large_text):
        scores["ui"] += 2
    if "font-mono" in text or "font-bold" in text:
        scores["ui"] += 1

    # Interactive feedback (3 pts): hover/active states
    if "hover:" in text:
        scores["ui"] += 2
    if "active:" in text or "transition" in text:
        scores["ui"] += 1

    # Dropdown styling for converters (2 pts)
    if any(t in text for t in ["<select", "select ", "dropdown", "combobox"]):
        scores["ui"] += 2

    # --- Build penalty ---
    if run_build and shutil.which("npm"):
        try:
            install = subprocess.run(
                ["npm", "install"],
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=300,
                check=False,
            )
            build = subprocess.run(
                ["npm", "run", "build"],
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=300,
                check=False,
            )
            if install.returncode != 0 or build.returncode != 0:
                scores["scaffold"] = max(scores["scaffold"] - 5, 0)
        except (OSError, subprocess.SubprocessError):
            scores["scaffold"] = max(scores["scaffold"] - 5, 0)

    # Anti-pattern penalty (applied to quality score)
    anti = _detect_anti_patterns(raw_text)
    scores["quality"] = max(scores["quality"] + anti["penalty"], 0)

    scores["total"] = sum(scores.values())
    return scores


@pytest.fixture()
def sample_calculator_project(tmp_path: Path) -> Path:
    project = tmp_path / "calculator-app"
    (project / "src" / "pages").mkdir(parents=True)
    (project / "src" / "components").mkdir(parents=True)
    (project / "src" / "hooks").mkdir(parents=True)
    (project / "src" / "services").mkdir(parents=True)
    (project / "src" / "constants").mkdir(parents=True)
    (project / "tests").mkdir(parents=True)

    (project / "package.json").write_text(
        json.dumps(
            {
                "name": "calculator-app",
                "dependencies": {
                    "react": "^18.0.0",
                    "react-dom": "^18.0.0",
                    "react-router-dom": "^6.0.0",
                    "mathjs": "^13.0.0",
                    "big.js": "^6.0.0",
                },
            },
        ),
        encoding="utf-8",
    )
    (project / "src" / "main.jsx").write_text("import React from 'react';", encoding="utf-8")
    (project / "src" / "App.jsx").write_text(
        "import { Routes, Route } from 'react-router-dom';"
        "import Layout from './components/Layout';"
        "export default function App(){return <Layout><Routes></Routes></Layout>}",
        encoding="utf-8",
    )
    (project / "src" / "components" / "Layout.jsx").write_text(
        "export default function Layout(){return <nav className='bg-gray-900 text-white"
        " shadow-lg rounded-xl'>navbar</nav>}",
        encoding="utf-8",
    )
    (project / "src" / "hooks" / "useCalculator.js").write_text(
        "export const useCalculator = () => {};",
        encoding="utf-8",
    )
    (project / "src" / "constants" / "conversions.js").write_text(
        "export const conversionFactors = {};",
        encoding="utf-8",
    )
    (project / "src" / "pages" / "Landing.jsx").write_text(
        "export default function Landing(){}",
        encoding="utf-8",
    )
    (project / "src" / "pages" / "RegularCalculator.jsx").write_text(
        "const ops = ['+','-','*','/']; const clear='clear'; const back='backspace';"
        "const danger='divide by zero error infinity';"
        "const ui='bg-gray-800 text-white grid-cols-4 gap-2 bg-orange-500 bg-indigo-500"
        " rounded-lg shadow-lg text-4xl font-mono font-bold hover:bg-gray-600"
        " active:scale-95 transition';",
        encoding="utf-8",
    )
    (project / "src" / "pages" / "ScientificCalculator.jsx").write_text(
        "import { evaluate } from 'mathjs'; const f='sin cos tan log ln sqrt pow factorial';"
        "const mode='degree radian';",
        encoding="utf-8",
    )
    (project / "src" / "pages" / "CurrencyConverter.jsx").write_text(
        "const url='https://api.frankfurter.dev/latest';"
        "async function load(){const r=await fetch(url);}"
        "const status='loading error';"
        "const codes='usd eur gbp jpy cad aud chf cny inr mxn';"
        "const direction='from currency to currency swap'; const cache='localStorage';"
        "const sel=<select className='bg-gray-800'></select>;",
        encoding="utf-8",
    )
    (project / "src" / "pages" / "UnitConverter.jsx").write_text(
        "const cats='length weight temperature volume speed';"
        "const refs='mile km kg lbs c f kelvin 273.15';"
        "const dir='fromUnit toUnit';",
        encoding="utf-8",
    )
    (project / "tests" / "smoke.test.js").write_text("test('smoke',()=>{});", encoding="utf-8")

    return project


def test_project_creation_rubric_scores_realistic_fixture(sample_calculator_project: Path) -> None:
    scores = score_react_calculator_project(sample_calculator_project, run_build=False)
    assert scores["total"] >= 60, scores
    assert scores["currency"] >= 10, scores
    assert scores["scientific"] >= 10, scores


@pytest.mark.integration()
@pytest.mark.benchmark()
def test_project_creation_real_life_task_external_project() -> None:
    """Score a generated real project from env-provided path."""
    project_dir = os.environ.get("AUTOCODE_BENCH_TARGET_DIR")
    if not project_dir:
        pytest.skip("Set AUTOCODE_BENCH_TARGET_DIR to run real-life project benchmark.")

    root = Path(project_dir).expanduser().resolve()
    if not root.exists():
        pytest.skip(f"Project path does not exist: {root}")

    run_build = os.environ.get("AUTOCODE_BENCH_RUN_NODE", "0") == "1"
    min_score = int(os.environ.get("AUTOCODE_BENCH_MIN_SCORE", "60"))
    scores = score_react_calculator_project(root, run_build=run_build)

    assert scores["total"] >= min_score, (
        f"score={scores['total']} < min_score={min_score}; details={scores}"
    )
