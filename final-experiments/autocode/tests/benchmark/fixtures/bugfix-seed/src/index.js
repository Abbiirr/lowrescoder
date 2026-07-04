/**
 * Utility module with intentional bugs for benchmark testing.
 *
 * Bug 1: capitalize() doesn't handle empty strings (throws on .charAt)
 * Bug 2: sumArray() uses wrong initial value (starts at 1 instead of 0)
 * Bug 3: findMax() returns undefined for single-element arrays (off-by-one)
 */

/**
 * Capitalize the first letter of a string.
 * BUG: Uses bracket access which is undefined for empty string, causing TypeError.
 */
function capitalize(str) {
  return str[0].toUpperCase() + str.slice(1);
}

/**
 * Sum all numbers in an array.
 * BUG: Initial accumulator is 1 instead of 0.
 */
function sumArray(arr) {
  let total = 1;
  for (const num of arr) {
    total += num;
  }
  return total;
}

/**
 * Find the maximum value in an array.
 * BUG: Loop starts at index 2 instead of 1, missing single-element arrays.
 */
function findMax(arr) {
  if (arr.length === 0) return undefined;
  let max = arr[0];
  for (let i = 2; i < arr.length; i++) {
    if (arr[i] > max) {
      max = arr[i];
    }
  }
  return max;
}

/**
 * Reverse a string. (Working correctly — no bugs)
 */
function reverseString(str) {
  return str.split('').reverse().join('');
}

/**
 * Check if a number is even. (Working correctly — no bugs)
 */
function isEven(n) {
  return n % 2 === 0;
}

module.exports = { capitalize, sumArray, findMax, reverseString, isEven };
