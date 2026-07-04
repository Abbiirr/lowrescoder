/**
 * Core utility functions.
 * NOTE: This file contains intentional bugs for the E2E-BugFix benchmark.
 */

/**
 * Add two numbers.
 * BUG: returns a - b instead of a + b.
 */
function add(a, b) {
  return a - b;
}

/**
 * Capitalize the first letter of a string.
 * BUG: returns str.toLowerCase() instead of first-letter uppercase.
 */
function capitalize(str) {
  return str.toLowerCase();
}

/**
 * Filter even numbers from an array.
 * BUG: filters odds (n % 2 !== 0) instead of evens (n % 2 === 0).
 */
function filterEvens(arr) {
  return arr.filter((n) => n % 2 !== 0);
}

module.exports = { add, capitalize, filterEvens };
