const { capitalize, sumArray, findMax, reverseString, isEven } = require('../src/index');

// --- Tests that PASS (5) ---

describe('reverseString', () => {
  test('reverses a normal string', () => {
    expect(reverseString('hello')).toBe('olleh');
  });

  test('reverses an empty string', () => {
    expect(reverseString('')).toBe('');
  });
});

describe('isEven', () => {
  test('returns true for even numbers', () => {
    expect(isEven(4)).toBe(true);
  });

  test('returns false for odd numbers', () => {
    expect(isEven(7)).toBe(false);
  });
});

describe('capitalize', () => {
  test('capitalizes a normal string', () => {
    expect(capitalize('hello')).toBe('Hello');
  });
});

// --- Tests that FAIL (3) — exposing the 3 bugs ---

describe('capitalize - edge case', () => {
  test('handles empty string without crashing', () => {
    expect(capitalize('')).toBe('');
  });
});

describe('sumArray', () => {
  test('sums an array of numbers correctly', () => {
    expect(sumArray([1, 2, 3])).toBe(6);
  });
});

describe('findMax', () => {
  test('finds max when it is at index 1', () => {
    expect(findMax([1, 10, 3])).toBe(10);
  });
});
