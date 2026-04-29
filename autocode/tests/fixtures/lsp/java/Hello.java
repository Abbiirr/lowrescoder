/**
 * Project-local Java fixture for deterministic LSP adapter tests.
 */
public class Hello implements Greeter {
    public static void main(String[] args) {
        Hello hello = new Hello();
        hello.greet("AutoCode");
    }

    @Override
    public String greet(String name) {
        return "Hello, " + name;
    }

    public Box<Hello> boxed() {
        return new Box<>(this);
    }
}

interface Greeter {
    String greet(String name);
}

class Box<T> {
    private final T value;

    Box(T value) {
        this.value = value;
    }

    T value() {
        return value;
    }
}

class Broken {
    void syntaxError() {
        String missingSemicolon = "intentional"
    }
}
