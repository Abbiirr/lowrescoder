"""Project-local Python fixture for deterministic LSP adapter tests."""


class NameBox:
    def __init__(self, value: str) -> None:
        self.value = value


class Greeter:
    def greet(self, box: NameBox) -> str:
        return f"Hello, {box.value}"


def run_greeter(greeter: Greeter) -> str:
    return greeter.greet(NameBox("AutoCode"))


def broken() -> str:
    return missing_local_symbol
