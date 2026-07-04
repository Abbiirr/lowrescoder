"""Tests for commit_stats — inspired by go-gitea/gitea contributor analytics.

gitea counts commits per author to build contribution graphs. A classic
harness-bench v2 pattern: assignment (= 1) instead of increment (+= 1)
resets every counter, so no author ever shows more than 1 commit.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def commit(author):
    return {"author": author, "hash": "abc"}


def test_single_author_three_commits():
    from commit_stats import count_commits_by_author
    commits = [commit("Alice"), commit("Alice"), commit("Alice")]
    result = count_commits_by_author(commits)
    assert result == {"Alice": 3}, f"got {result}"


def test_two_authors_correct_counts():
    from commit_stats import count_commits_by_author
    commits = [commit("Alice"), commit("Bob"), commit("Alice"), commit("Bob"), commit("Bob")]
    result = count_commits_by_author(commits)
    assert result == {"Alice": 2, "Bob": 3}, f"got {result}"


def test_single_commit_is_one():
    from commit_stats import count_commits_by_author
    result = count_commits_by_author([commit("Solo")])
    assert result == {"Solo": 1}


def test_empty_returns_empty():
    from commit_stats import count_commits_by_author
    assert count_commits_by_author([]) == {}


def test_top_contributor_correct():
    from commit_stats import top_contributor
    commits = [commit("Alice"), commit("Bob"), commit("Bob"), commit("Bob"), commit("Alice")]
    assert top_contributor(commits) == "Bob"


def test_top_contributor_single():
    from commit_stats import top_contributor
    assert top_contributor([commit("Only")]) == "Only"


def test_top_contributor_empty():
    from commit_stats import top_contributor
    assert top_contributor([]) == ""
