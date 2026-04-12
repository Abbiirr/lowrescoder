"""Pattern-based permission rules (deep-research-report Phase B Item 5).

Claude Code's permission model uses pattern rules like ``Bash(npm run test *)``
that match the command prefix with a glob-style wildcard. The rule set
supports **deny-first precedence** — a single deny match wipes out any
allow match — and the tool supports **inline unit tests** so a rule set
can be validated before it goes live.

This module ships three pieces:

1. :class:`PermissionRule` — a parsed rule with a pattern, an effect
   (``allow`` or ``deny``), and an optional ``matches``/``not_matches``
   test list for self-verification.
2. :func:`evaluate` — deny-first precedence check for a ``(tool, target)``
   pair against a list of rules.
3. :func:`validate_rules` — run every rule's inline tests and collect
   errors so the caller can reject a bad rule set before it takes effect.

Rule pattern grammar (deliberately tiny — easy to audit):

    <Tool>(<spec>)

where ``<Tool>`` is one of ``Bash``, ``Read``, ``Write``, ``Edit``,
``WebFetch``, or any tool name registered in the live tool registry.
``<spec>`` is a glob-style pattern that matches against a "target"
string passed by the caller (e.g. the bash command string for ``Bash``,
the path for ``Read``/``Write``/``Edit``, the URL for ``WebFetch``).

Glob semantics:

- ``*`` matches any run of non-whitespace characters
- ``**`` matches any substring (including whitespace)
- anything else is literal

Examples:

- ``Bash(npm run test *)`` — matches ``npm run test --coverage`` but not
  ``npm run start``
- ``Bash(git status)`` — exact match only
- ``Read(**/*.py)`` — any .py file anywhere
- ``WebFetch(https://api.github.com/**)`` — any GitHub API URL
"""

from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass, field
from typing import Literal

Effect = Literal["allow", "deny"]


_RULE_HEADER = re.compile(r"^\s*(\w+)\s*\(\s*(.*?)\s*\)\s*$")


@dataclass
class PermissionRule:
    """A single parsed permission rule with optional inline tests."""

    tool: str
    pattern: str
    effect: Effect
    #: Inline test cases that must match this rule.
    matches: list[str] = field(default_factory=list)
    #: Inline test cases that must NOT match this rule.
    not_matches: list[str] = field(default_factory=list)

    def test(self, target: str) -> bool:
        """Return True if ``target`` matches this rule's pattern.

        Uses fnmatch semantics — ``*`` matches any run of characters.
        For stricter "non-whitespace only" semantics (Claude Code's
        actual rule grammar), callers should apply whitespace-splitting
        on the target side before calling.
        """
        return fnmatch.fnmatchcase(target, self.pattern)

    def run_self_tests(self) -> list[str]:
        """Run the rule's inline ``matches``/``not_matches`` tests.

        Returns a list of human-readable errors (empty if all pass).
        """
        errors: list[str] = []
        for good in self.matches:
            if not self.test(good):
                errors.append(
                    f"{self.tool}({self.pattern}) should match {good!r} but does not"
                )
        for bad in self.not_matches:
            if self.test(bad):
                errors.append(
                    f"{self.tool}({self.pattern}) should NOT match {bad!r} but does"
                )
        return errors


def parse_rule(
    header: str,
    effect: Effect,
    *,
    matches: list[str] | None = None,
    not_matches: list[str] | None = None,
) -> PermissionRule:
    """Parse a ``Tool(spec)`` header into a :class:`PermissionRule`.

    Args:
        header: Header string like ``Bash(npm run test *)``.
        effect: ``"allow"`` or ``"deny"``.
        matches: Optional list of targets that must match.
        not_matches: Optional list of targets that must NOT match.

    Raises:
        ValueError: If the header is malformed.
    """
    m = _RULE_HEADER.match(header)
    if not m:
        raise ValueError(
            f"invalid rule header {header!r} — expected Tool(spec)"
        )
    tool, pattern = m.group(1), m.group(2)
    if effect not in ("allow", "deny"):
        raise ValueError(f"effect must be 'allow' or 'deny', got {effect!r}")
    return PermissionRule(
        tool=tool,
        pattern=pattern,
        effect=effect,
        matches=list(matches or []),
        not_matches=list(not_matches or []),
    )


@dataclass
class Decision:
    """Outcome of evaluating a ``(tool, target)`` pair against a rule set."""

    effect: Effect
    reason: str
    matched_rule: PermissionRule | None = None


def evaluate(
    tool: str,
    target: str,
    rules: list[PermissionRule],
    *,
    default: Effect = "allow",
) -> Decision:
    """Evaluate ``(tool, target)`` against ``rules`` with deny-first precedence.

    Semantics:

    - Any ``deny`` rule that matches **immediately** wins, regardless of
      allow rules.
    - If no ``deny`` matches but at least one ``allow`` matches, the
      result is ``allow``.
    - If nothing matches, the result is ``default`` (``"allow"`` by
      default, matching the current lax posture; callers can tighten
      to ``"deny"`` for fail-closed setups).
    """
    matched_deny: PermissionRule | None = None
    matched_allow: PermissionRule | None = None

    for rule in rules:
        if rule.tool != tool:
            continue
        if not rule.test(target):
            continue
        if rule.effect == "deny":
            matched_deny = rule
            break
        if matched_allow is None:
            matched_allow = rule

    if matched_deny is not None:
        return Decision(
            effect="deny",
            reason=f"denied by rule {matched_deny.tool}({matched_deny.pattern})",
            matched_rule=matched_deny,
        )
    if matched_allow is not None:
        return Decision(
            effect="allow",
            reason=f"allowed by rule {matched_allow.tool}({matched_allow.pattern})",
            matched_rule=matched_allow,
        )
    return Decision(
        effect=default,
        reason=f"no matching rule ({default} by default)",
        matched_rule=None,
    )


def validate_rules(rules: list[PermissionRule]) -> list[str]:
    """Run every rule's inline self-tests. Returns a flat error list."""
    errors: list[str] = []
    for rule in rules:
        errors.extend(rule.run_self_tests())
    return errors
