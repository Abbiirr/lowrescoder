# B15-B29 Portfolio

This document restores the extended `B15`-`B29` benchmark portfolio that sits
on top of the existing benchmark harness.

## Why These Lanes Exist

The older benchmark mix is useful for regression tracking, but it is vulnerable
to benchmark-maxing because it leans on public issue-fix suites and narrow
proxy lanes. `B15`-`B29` were designed to cover the missing agent behaviors:

- intake parsing from natural prompts
- product-requirement implementation
- longer maintenance work
- freshness proxies
- mixed-domain repo work
- shell and git recovery
- regression preservation
- corrupted state repair
- collaborator drift recovery
- security patching
- proposal evaluation
- economic-value tasks
- efficiency under budget
- repeatability
- resilience to transient faults

## Portfolio Table

| Lane | Name | Restored Task Count | Runner | Status |
|------|------|---------------------|--------|--------|
| B15 | Realistic Intake Mutation | 1 | `swebench` | runnable prototype |
| B16 | Requirement-Driven Feature Delivery | 1 | `swebench` | runnable prototype |
| B17 | Long-Horizon Multi-File Maintenance | 1 | `swebench` | runnable prototype |
| B18 | Fresh Held-Out Issue Resolution | 1 | `competitive` | runnable stand-in |
| B19 | Multilingual Repository Work | 3 | `swebench` | runnable prototype |
| B20 | Terminal, Git, and Ops Recovery | 1 | `swebench` | runnable prototype |
| B21 | Regression and Contract Preservation | 1 | `swebench` | runnable prototype |
| B22 | Corrupted State Recovery | 1 | `swebench` | runnable prototype |
| B23 | Collaborative Out-of-Sync Recovery | 1 | `swebench` | runnable prototype |
| B24 | Security Audit and Safe Patching | 1 | `swebench` | runnable prototype |
| B25 | Managerial Review and Proposal Selection | 1 | `swebench` | runnable stand-in |
| B26 | Economic-Value Freelance Tasks | 1 | `swebench` | runnable prototype |
| B27 | Efficiency Under Budget | 1 | `swebench` | runnable prototype |
| B28 | Reliability and Repeatability | 1 | `swebench` | runnable prototype |
| B29 | Fault Injection and Infra Resilience | 1 | `swebench` | runnable prototype |

## Notes

- Total restored prototype batch size: `17` tasks.
- `B18` and `B25` remain explicit stand-ins, not canonical external parity lanes.
- The current restored manifests prioritize local reproducibility over external
  claim-making. All parity claims remain forbidden.
