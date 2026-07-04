# TASK-083: Fix Git Argument Joiner Separator (jesseduffield/lazygit pattern)

## Source
Inspired by jesseduffield/lazygit command building. Arguments must be joined
with a space, not a comma, to form a valid shell command string.

## Goal
Fix `src/arg_builder.py` so `build_git_args()` joins with `' '` (space).

## The bug
```python
# BUG: comma separator
return ','.join(base_args + extra_args)

# Fix: space separator
return ' '.join(base_args + extra_args)
```

## Failing tests (3/7 fail initially)
```
test_single_extra_arg_space_separated ← FAILS ('git,log' != 'git log')
test_no_commas_in_output              ← FAILS (comma found)
test_space_separated_multiple         ← FAILS (comma-joined)
```
