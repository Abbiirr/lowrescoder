const { add, capitalize, filterEvens } = require("../src/index");
const { clamp, isPalindrome } = require("../src/utils");

// --- Tests for src/index.js (3 bugs → 3 failures expected) ---

describe("add", () => {
  test("adds two positive numbers", () => {
    expect(add(2, 3)).toBe(5);
  });
});

describe("capitalize", () => {
  test("capitalizes the first letter", () => {
    expect(capitalize("hello")).toBe("Hello");
  });
});

describe("filterEvens", () => {
  test("returns only even numbers", () => {
    expect(filterEvens([1, 2, 3, 4, 5, 6])).toEqual([2, 4, 6]);
  });
});

// --- Tests for src/utils.js (correct → 2 passes expected) ---

describe("clamp", () => {
  test("clamps value within range", () => {
    expect(clamp(5, 1, 10)).toBe(5);
    expect(clamp(-3, 0, 100)).toBe(0);
    expect(clamp(999, 0, 100)).toBe(100);
  });
});

describe("isPalindrome", () => {
  test("detects palindromes correctly", () => {
    expect(isPalindrome("racecar")).toBe(true);
    expect(isPalindrome("hello")).toBe(false);
    expect(isPalindrome("A man a plan a canal Panama")).toBe(true);
  });
});
