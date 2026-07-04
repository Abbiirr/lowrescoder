/**
 * Project-local TypeScript fixture for deterministic LSP adapter tests.
 */
export interface Greeter<T> {
  greet(value: T): string;
}

export type NameBox<T> = {
  value: T;
};

export class LocalGreeter implements Greeter<NameBox<string>> {
  greet(value: NameBox<string>): string {
    return `Hello, ${value.value}`;
  }
}

export function runGreeter(greeter: Greeter<NameBox<string>>): string {
  return greeter.greet({ value: "AutoCode" });
}

const broken: number = "intentional type error";
