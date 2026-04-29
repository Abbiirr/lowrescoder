/**
 * Project-local JavaScript fixture for deterministic LSP adapter tests.
 */
export function greet(name) {
  return `Hello, ${name}`;
}

export function run() {
  return greet("AutoCode");
}

class LocalGreeter {
  greet(name) {
    return greet(name);
  }
}

const greeter = new LocalGreeter();
greeter.greet("JS");

function broken() {
  return missingLocalValue;
}
