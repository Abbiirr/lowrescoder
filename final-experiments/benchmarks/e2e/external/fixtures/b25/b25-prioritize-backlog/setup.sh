#!/usr/bin/env bash
set -euo pipefail

mkdir -p project

cat > project/backlog.md << 'EOF'
# Product Backlog

| ID | Task | Effort | Impact | Notes |
|----|------|--------|--------|-------|
| T1 | Fix login timeout bug | S | high | Users locked out after 5 min idle |
| T2 | Redesign dashboard UI | L | med | Visual refresh, no new functionality |
| T3 | Add CSV export | S | high | Top customer request, 30+ tickets |
| T4 | Migrate to new payment API | L | high | Current API deprecated in 6 months |
| T5 | Add dark mode | M | low | Nice-to-have, 3 user requests |
| T6 | Fix email notification encoding | S | med | Accented names show as garbled |
| T7 | Implement audit logging | M | high | Required for compliance by Q3 |
| T8 | Upgrade to Python 3.12 | M | low | Performance gains, no user-facing change |
| T9 | Add two-factor authentication | M | high | Security requirement from enterprise clients |
| T10 | Refactor database queries | L | med | Tech debt, 3x slower than needed |

## Effort Scale
- **S (Small):** < 1 developer-week
- **M (Medium):** 1-3 developer-weeks
- **L (Large):** 3+ developer-weeks

## Impact Scale
- **low:** Nice-to-have, minimal user/business impact
- **med:** Useful improvement, moderate user/business impact
- **high:** Critical for users, revenue, or compliance
EOF

cat > project/priority_template.md << 'EOF'
# Prioritized Backlog

## Tier 1: Do First (Sprint 1-2)
| Priority | ID | Task | Effort | Impact | Rationale |
|----------|----|------|--------|--------|-----------|
| 1 | | | | | |

## Tier 2: Do Next (Sprint 3-4)
| Priority | ID | Task | Effort | Impact | Rationale |
|----------|----|------|--------|--------|-----------|

## Tier 3: Do Later (Sprint 5+)
| Priority | ID | Task | Effort | Impact | Rationale |
|----------|----|------|--------|--------|-----------|

## Tier 4: Consider Dropping / Deferring
| ID | Task | Rationale |
|----|------|-----------|

## Prioritization Methodology
<!-- Explain your prioritization approach (e.g., impact/effort matrix, MoSCoW, etc.) -->
EOF

echo "Setup complete. 10 backlog items ready for prioritization."
