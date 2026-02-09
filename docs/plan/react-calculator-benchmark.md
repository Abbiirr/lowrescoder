# React Calculator App Benchmark

> HybridCoder — Edge-Native AI Coding Assistant
> Version: 1.0 | Date: 2026-02-09
> Purpose: Real-world benchmark for agentic task completion (Tier 4)
> Phase: 5-6 (requires agentic workflow + edit system)

---

## 1. Purpose

Test whether HybridCoder can autonomously scaffold and build a complete web application from a single natural language prompt. This is the most realistic test of an AI coding agent because it requires:

- **Multi-file coordination** (25+ files created in a coherent project structure)
- **Architecture decisions** (component hierarchy, state management, routing)
- **External API integration** (live currency exchange rates)
- **Mathematical correctness** (scientific calculator functions)
- **UX considerations** (error handling, loading states, responsive layout)

None of the major competitors (Aider, Continue.dev, Cursor, Claude Code) explicitly benchmark this "build from scratch" capability. Their benchmarks focus on editing existing code or solving isolated problems. This test fills that gap.

---

## 2. The Task

### Prompt (Single Message to HybridCoder)

> Create a React web app with a landing page and 4 calculator pages: regular calculator, scientific calculator, currency converter (using Frankfurter API), and unit converter (length, weight, temperature, volume, speed). Use Vite, React Router v6, Tailwind CSS, mathjs for scientific calculations, and big.js for decimal precision. Include proper error handling and a clean, modern UI.

### Expected Output

A complete, runnable React application that:
- Starts with `npm install && npm run dev`
- Has 5 navigable pages (landing + 4 calculators)
- All calculators produce correct results
- Has a clean, consistent UI
- Handles errors gracefully

---

## 3. Technology Stack (Expected)

| Component | Technology | Why |
|-----------|-----------|-----|
| Framework | React 18+ | Industry standard |
| Build tool | Vite | Fast, modern, zero-config |
| Routing | React Router v6 | Standard React routing |
| Styling | Tailwind CSS | Utility-first, rapid development |
| Scientific math | mathjs | Expression parsing, trig, log, factorial |
| Decimal precision | big.js | Avoid floating-point errors in calculator |
| Currency rates | Frankfurter API | Free, no API key, reliable |

**Frankfurter API:**
- Base URL: `https://api.frankfurter.dev`
- Endpoint: `GET /latest?base=USD&symbols=EUR,GBP,JPY,...`
- No API key required
- Rate-limited but sufficient for a calculator app
- Returns JSON: `{"base":"USD","date":"2026-02-09","rates":{"EUR":0.92,...}}`

---

## 4. Evaluation Criteria

### 4.1 Scaffold Quality (20 points)

| Criterion | Points | How to Verify |
|-----------|--------|---------------|
| Project initializes with Vite + React | 5 | `npm create vite` or equivalent scaffold exists |
| React Router configured with 5+ routes | 5 | Routes defined for landing, regular, scientific, currency, unit |
| Shared layout component (header, nav, footer) | 5 | Common layout wrapping all pages |
| Clean directory structure | 5 | Organized into pages/, components/, hooks/, services/ or similar |

**What "clean directory structure" means:**
```
src/
  pages/           (or views/ or routes/)
    Landing.jsx
    RegularCalc.jsx
    ScientificCalc.jsx
    CurrencyConverter.jsx
    UnitConverter.jsx
  components/       (shared UI components)
    Layout.jsx
    Button.jsx
    Display.jsx
    ...
  hooks/            (custom React hooks)
    useCalculator.js
    useCurrency.js
    ...
  services/         (API clients, utilities)
    currencyApi.js
    conversions.js
    ...
  App.jsx
  main.jsx
```

Any reasonable organization is acceptable. Flat structure (everything in src/) loses points.

### 4.2 Regular Calculator (15 points)

| Criterion | Points | How to Verify |
|-----------|--------|---------------|
| All basic operations work (+, -, *, /) | 5 | Test: 2+3=5, 10-4=6, 3*7=21, 15/3=5 |
| Display shows input and result | 5 | Visual check: input expression visible, result displayed |
| Clear/backspace functional | 3 | C clears all, backspace removes last char |
| Edge cases handled | 2 | Division by zero shows error, large numbers don't crash |

**Test cases for regular calculator:**
```
2 + 3 = 5
10 - 4 = 6
3 * 7 = 21
15 / 3 = 5
100 / 0 = Error (or Infinity with message)
0.1 + 0.2 = 0.3 (not 0.30000000000000004 — big.js should handle this)
999999999 * 999999999 = 999999998000000001 (or handled gracefully)
```

### 4.3 Scientific Calculator (20 points)

| Criterion | Points | How to Verify |
|-----------|--------|---------------|
| Trig functions (sin, cos, tan) | 5 | sin(30°)=0.5, cos(0)=1, tan(45°)=1 |
| Log/ln functions | 5 | log(100)=2, ln(e)=1 |
| Expression parsing with parentheses | 5 | (2+3)*4=20, 2*(3+4)=14 |
| Factorial, power operations | 3 | 5!=120, 2^10=1024 |
| Degree/radian toggle | 2 | sin(π/2 rad)=1, sin(90°)=1 |

**Test cases for scientific calculator:**
```
sin(30) in degree mode = 0.5
sin(π/6) in radian mode = 0.5
cos(0) = 1
tan(45) in degree mode = 1
log(100) = 2 (base 10)
ln(e) = 1 (natural log)
5! = 120
2^10 = 1024
(2+3)*4 = 20
sqrt(144) = 12
```

### 4.4 Currency Converter (20 points)

| Criterion | Points | How to Verify |
|-----------|--------|---------------|
| Fetches live exchange rates | 5 | Network tab shows successful API call |
| Two-way conversion works | 5 | USD→EUR and EUR→USD both calculate correctly |
| Currency selector with 10+ currencies | 3 | Dropdown/select with USD, EUR, GBP, JPY, CAD, AUD, CHF, CNY, INR, MXN+ |
| Error handling for API failures | 3 | Disconnect network → shows error message, doesn't crash |
| Loading states shown | 2 | Spinner/skeleton while fetching rates |
| Rate caching | 2 | Second conversion doesn't re-fetch (check network tab) |

**Test procedure for currency converter:**
1. Select USD → EUR, enter 100, verify result matches Frankfurter rate
2. Swap to EUR → USD, verify reverse calculation
3. Try 10+ different currency pairs
4. Disconnect network, try conversion → should show error
5. Reconnect, verify recovery

### 4.5 Unit Converter (15 points)

| Criterion | Points | How to Verify |
|-----------|--------|---------------|
| At least 3 unit categories | 5 | Length, weight, temperature at minimum |
| Correct conversion values | 5 | 1 mile = 1.60934 km, 1 kg = 2.20462 lbs, 100°C = 212°F |
| Bidirectional conversion | 3 | km→miles and miles→km both work |
| Temperature handles non-linear conversion | 2 | C→F: (C*9/5)+32, F→C: (F-32)*5/9, includes Kelvin |

**Test cases for unit converter:**

Length:
```
1 mile = 1.60934 km
1 km = 0.621371 miles
1 meter = 3.28084 feet
1 inch = 2.54 cm
```

Weight:
```
1 kg = 2.20462 lbs
1 lb = 0.453592 kg
1 oz = 28.3495 grams
```

Temperature:
```
0°C = 32°F
100°C = 212°F
-40°C = -40°F
0°C = 273.15K
-273.15°C = 0K
```

Volume (bonus):
```
1 gallon = 3.78541 liters
1 liter = 0.264172 gallons
```

Speed (bonus):
```
1 mph = 1.60934 km/h
100 km/h = 62.1371 mph
```

### 4.6 Code Quality (10 points)

| Criterion | Points | How to Verify |
|-----------|--------|---------------|
| Custom hooks for business logic | 3 | At least 1 custom hook (e.g., useCalculator, useCurrency) |
| No hardcoded values (constants file) | 3 | Conversion factors in a constants file, not inline |
| Consistent code style | 2 | Same formatting, naming conventions throughout |
| No console errors | 2 | Browser devtools console clean on all pages |

---

## 5. Scoring

### Total: 100 Points

| Category | Max Points |
|----------|-----------|
| Scaffold Quality | 20 |
| Regular Calculator | 15 |
| Scientific Calculator | 20 |
| Currency Converter | 20 |
| Unit Converter | 15 |
| Code Quality | 10 |
| **Total** | **100** |

### Scoring Tiers

| Score | Tier | Description |
|-------|------|-------------|
| 90-100 | Production-quality | Exceeds expectations. All calculators work correctly, clean code, good UX. |
| 70-89 | Good | Works with minor issues. Most calculators functional, some edge cases missed. |
| 50-69 | Acceptable | Core features work. Some calculators may have bugs or missing features. |
| 30-49 | Partial | Some calculators work, others broken. App runs but with significant gaps. |
| 0-29 | Failed | App doesn't run, or major features completely missing. |

### Bonus Points (Not in Base Score)

These don't count toward the 100-point score but are noted for exceptional implementations:

| Bonus | Points | Criterion |
|-------|--------|-----------|
| Responsive design | +5 | Works on mobile viewport (375px) |
| Accessibility | +5 | Keyboard navigation, aria labels, screen reader friendly |
| Dark mode | +3 | Toggle between light/dark themes |
| History/memory | +3 | Calculator remembers previous calculations |
| Animations | +2 | Smooth transitions between pages/states |
| Tests included | +5 | Any automated tests (Jest, Vitest, Playwright) |

---

## 6. Test Procedure

### Prerequisites

- Node.js 20+ installed
- npm or pnpm available
- Clean empty directory for project creation
- Internet access (for Frankfurter API and npm packages)

### Step 1: Setup

```bash
mkdir test-calculator-app
cd test-calculator-app
```

### Step 2: Run HybridCoder

Launch HybridCoder and provide the single prompt from Section 2.

**Time limit:** 30 minutes for complete project creation. HybridCoder should autonomously:
1. Initialize the Vite + React project
2. Install dependencies (tailwindcss, react-router-dom, mathjs, big.js)
3. Configure Tailwind CSS
4. Create all pages, components, hooks, and services
5. Set up routing
6. Implement all 4 calculators

### Step 3: Build Verification

```bash
npm install          # Should succeed with 0 errors
npm run build        # Should succeed with 0 errors
npm run dev          # Should start dev server
```

**Automated checks:**
- `npm install` exit code 0
- `npm run build` exit code 0
- No TypeScript/ESLint errors in build output

### Step 4: Manual Testing

Navigate each page and test all calculators per the criteria in Section 4.

Score each criterion independently using the rubric.

### Step 5: Automated Testing (Optional)

If time permits, run basic Playwright tests:

```javascript
// tests/calculators.spec.js
test('landing page loads', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveTitle(/calculator/i);
});

test('regular calculator: 2+3=5', async ({ page }) => {
  await page.goto('/calculator');
  // Click buttons: 2, +, 3, =
  // Assert display shows 5
});

test('currency converter fetches rates', async ({ page }) => {
  await page.goto('/currency');
  // Wait for loading to complete
  // Assert rate display is not empty
});
```

### Step 6: Scoring

Fill out the scoring sheet:

```
## Score Sheet — React Calculator Benchmark
Date: ____
HybridCoder Version: ____
Model: ____

### Scaffold Quality (20)
- [ ] (5) Vite + React initialized
- [ ] (5) React Router with 5+ routes
- [ ] (5) Shared layout component
- [ ] (5) Clean directory structure
Subtotal: __/20

### Regular Calculator (15)
- [ ] (5) Basic operations work
- [ ] (5) Display shows input/result
- [ ] (3) Clear/backspace work
- [ ] (2) Edge cases handled
Subtotal: __/15

### Scientific Calculator (20)
- [ ] (5) Trig functions work
- [ ] (5) Log/ln functions work
- [ ] (5) Expression parsing with parens
- [ ] (3) Factorial, powers work
- [ ] (2) Degree/radian toggle
Subtotal: __/20

### Currency Converter (20)
- [ ] (5) Fetches live rates
- [ ] (5) Two-way conversion
- [ ] (3) 10+ currencies
- [ ] (3) Error handling
- [ ] (2) Loading states
- [ ] (2) Rate caching
Subtotal: __/20

### Unit Converter (15)
- [ ] (5) 3+ unit categories
- [ ] (5) Correct conversion values
- [ ] (3) Bidirectional conversion
- [ ] (2) Non-linear temperature
Subtotal: __/15

### Code Quality (10)
- [ ] (3) Custom hooks
- [ ] (3) No hardcoded values
- [ ] (2) Consistent style
- [ ] (2) No console errors
Subtotal: __/10

### TOTAL: __/100
### TIER: ____
```

---

## 7. Expected Component Count

Based on analysis of similar React calculator apps:

| Category | Expected Count | Range |
|----------|---------------|-------|
| React components | 25-35 | 20-45 |
| Custom hooks | 3-5 | 2-8 |
| Service files | 2-3 | 1-5 |
| Constants/config files | 1-2 | 1-3 |
| Total LOC (excl. tests) | 3500-4000 | 2500-5000 |
| Total LOC (with tests) | 5000-6000 | 4000-7000 |
| Total files | 30-40 | 25-50 |

---

## 8. Why This Test Matters

### Capabilities Tested

1. **Project scaffolding**: Can the agent initialize a project from scratch with the right tools (Vite, not CRA)?
2. **Multi-file coordination**: 30+ files need to be created that reference each other correctly (imports, routes, components).
3. **Architecture decisions**: How does the agent organize components? Does it create a shared layout? Custom hooks? Service files?
4. **External API integration**: The currency converter requires making HTTP requests, handling loading/error states, and caching.
5. **Mathematical correctness**: Scientific calculator must handle trig, log, factorial correctly — not approximately, but exactly (within floating-point limits).
6. **Real-world complexity**: This is not a toy problem. A 100-point rubric across 6 categories tests multiple dimensions simultaneously.

### What Sets This Apart from Existing Benchmarks

| Existing Benchmark | What It Tests | What It Misses |
|--------------------|--------------|---------------|
| HumanEval | Single function completion | Multi-file, architecture |
| SWE-Bench | Bug fixing in existing code | Building from scratch |
| Aider Edit | Editing single files | Project creation, routing, API integration |
| Aider Polyglot | Multi-language edits | Full application architecture |

The React Calculator benchmark fills the gap: **building a complete application from scratch, testing both correctness and architecture quality.**

### Reproducibility

This benchmark is fully reproducible:
- The prompt is fixed (Section 2)
- The rubric is quantitative (Section 4)
- The test cases have expected values (Sections 4.2-4.5)
- The scoring tiers are defined (Section 5)
- The procedure is documented (Section 6)

Any AI coding agent can be evaluated against this same rubric, enabling fair comparison across tools.

---

## 9. Baseline Expectations

### For Qwen3-8B via HybridCoder (Phase 5-6)

| Metric | Conservative | Optimistic |
|--------|-------------|-----------|
| Total score | 40-55 | 60-75 |
| Scaffold quality | 15/20 | 20/20 |
| Regular calculator | 10/15 | 15/15 |
| Scientific calculator | 8/20 | 15/20 |
| Currency converter | 5/20 | 15/20 |
| Unit converter | 8/15 | 12/15 |
| Code quality | 4/10 | 8/10 |

**Why conservative?** A 7B model has limited multi-file coordination ability. The scientific calculator and currency converter are the hardest parts (expression parsing, async API calls, error handling). The regular calculator and unit converter are more straightforward.

### For Comparison (Hypothetical)

| Agent | Expected Score | Notes |
|-------|---------------|-------|
| Claude Code (Opus) | 80-95 | Large cloud model, excellent at multi-file |
| Aider (GPT-4) | 65-80 | Good editing, weaker at project creation |
| Cursor (GPT-4) | 70-85 | IDE context helps, but CLI benchmark |
| HybridCoder (Qwen3-8B) | 40-75 | Depends heavily on context quality |
| Raw Qwen3-8B (no context) | 20-40 | Would struggle with multi-file coordination |
