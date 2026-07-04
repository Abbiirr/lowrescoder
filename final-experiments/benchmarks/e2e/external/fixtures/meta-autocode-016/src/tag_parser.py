# Tag parser for note content — has a bug.
# This file exists to be fixed by the agent.


def extract_tags(content: str) -> list[str]:
    """Extract hashtags from note content.

    Tags are words starting with '#'. The tag name is the word minus the '#'
    prefix and any trailing punctuation (.,!?;:).

    Bug: returns the raw word slice after '#', including trailing punctuation.
    "#bug." should yield "bug", not "bug.".
    "#hello," should yield "hello", not "hello,".

    Fix: strip trailing punctuation from each extracted tag.
    """
    tags = []
    for word in content.split():
        if word.startswith("#") and len(word) > 1:
            # BUG: includes trailing punctuation in tag name
            tags.append(word[1:])
    return tags
