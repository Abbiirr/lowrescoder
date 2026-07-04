/**
 * Helper utilities (correct — regression baseline).
 */

/**
 * Clamp a value between min and max.
 */
function clamp(val, min, max) {
  if (val < min) return min;
  if (val > max) return max;
  return val;
}

/**
 * Check if a string is a palindrome (case-insensitive).
 */
function isPalindrome(str) {
  const cleaned = str.toLowerCase().replace(/[^a-z0-9]/g, "");
  return cleaned === cleaned.split("").reverse().join("");
}

module.exports = { clamp, isPalindrome };
