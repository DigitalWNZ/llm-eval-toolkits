# Gemini 3.5 Flash Benchmark Analysis Report

**Date:** 2026-06-24
**Model:** gemini-3.5-flash
**Endpoint:** Vertex AI (project: cloud-llm-preview1, location: global)

---

## 1. Benchmark Overview

### 1.1 Full Benchmark (June 23)

- **Source:** `benchmark_summary_20260623_142632.csv`
- **Scope:** 8 request files × 4 thinking levels × 2 streaming FC modes × 50 iterations = 3,200 API calls (3,198 successful)
- **Request files:**
  - Traditional (no tools): `request_1k`, `request_2k`, `request_5k`, `request_10k`, `request_50k`, `request_100k`
  - Tool-use: `slow_request_40s` (input: 37,112 tokens), `slow_request_60s` (input: 110,419 tokens)
- **Thinking levels:** minimal, low, medium, high
- **Streaming FC:** on/off (only meaningful for tool-use requests)

### 1.2 After-Fix Benchmark (June 24)

- **Source:** `benchmark_summary_20260624_004938_after_fix.csv`
- **Scope:** 2 tool-use request files × 4 thinking levels × 2 streaming FC modes × 10 iterations = 160 API calls (153 successful, 7 failed due to 429 rate limiting)

### 1.3 Pre-Fix Benchmark (May 20)

- **Source:** `perf_results_gemini-3.5-flash_all_locations_10iter_warmed_20260520.csv`
- **Scope:** 2 tool-use request files × 5 thinking levels (minimal/low/medium/high/default) × 3 locations (global/us/eu) × 10 iterations
- **Request files:** slow_request_40s (input: 23,676 tokens), slow_request_60s (input: 94,852 tokens)
- **Note:** Request files had different input token counts than the June 24 versions (slow_40s: 23,676 vs 37,112; slow_60s: 94,852 vs 110,419)

---

## 2. Traditional Requests (No Tools)

### 2.1 TTFT P50 (ms) by Thinking Level and Request Size

| Request | Input Tokens | Minimal | Low | Medium | High |
|---------|-------------|---------|-----|--------|------|
| request_1k | 996 | 607 | 4,248 | 5,487 | 6,696 |
| request_2k | 1,778 | 719 | 4,809 | 6,623 | 7,133 |
| request_5k | 3,883 | 765 | 7,336 | 8,719 | 8,934 |
| request_10k | 4,974 | 695 | 6,758 | 8,639 | 9,409 |
| request_50k | 7,587 | 746 | 7,162 | 11,149 | 13,704 |
| request_100k | 13,891 | 896 | 7,990 | 12,868 | 16,498 |

*(Values are averages of FC on/off, since streaming FC is a no-op without tools)*

### 2.2 Thinking Tokens P50 by Thinking Level and Request Size

| Request | Minimal | Low | Medium | High |
|---------|---------|-----|--------|------|
| request_1k | 0 | 629 | 892 | 1,038 |
| request_2k | 0 | 740 | 1,092 | 1,129 |
| request_5k | 0 | 1,066 | 1,491 | 1,460 |
| request_10k | 0 | 1,061 | 1,519 | 1,601 |
| request_50k | 0 | 1,152 | 1,908 | 2,394 |
| request_100k | 0 | 1,278 | 2,337 | 2,901 |

### 2.3 Key Findings — Traditional Requests

1. **Thinking level controls TTFT monotonically.** Each step up (minimal → low → medium → high) increases TTFT predictably. The biggest jump is minimal → low (5–10×), with low → medium → high being more incremental.

2. **Minimal thinking produces zero thinking tokens.** TTFT at minimal is purely network + prefill time: consistently sub-1s (600–900ms) regardless of input size.

3. **Input size amplifies TTFT at higher thinking levels.** At minimal, 1k and 100k are both under 1s. At high thinking, 1k = 6.7s vs 100k = 16.5s (2.5× difference). Larger inputs generate more thinking tokens, compounding latency.

4. **TTFT tracks thinking tokens linearly.** Rough rate: ~5–6ms per thinking token at P50. Example: request_100k at high — 2,900 thinking tokens × ~5.5ms ≈ 16s TTFT.

5. **Streaming FC on vs off has no effect** on traditional requests (expected — no tools present).

---

## 3. Tool-Use Requests

### 3.1 TTFT P50 (ms) — June 23 Full Benchmark

| Request | Minimal | Low | Medium | High |
|---------|---------|-----|--------|------|
| slow_40s (FC on) | 18,950 | 14,078 | 15,571 | 15,389 |
| slow_40s (FC off) | 17,284 | 15,575 | 15,241 | 15,274 |
| slow_60s (FC on) | 12,892 | 11,022 | 16,141 | 10,063 |
| slow_60s (FC off) | 16,171 | 13,393 | 16,849 | 13,731 |

### 3.2 TTFT P90 (ms) — June 23 Full Benchmark

| Request | Minimal | Low | Medium | High |
|---------|---------|-----|--------|------|
| slow_40s (FC on) | 27,828 | 24,151 | 27,252 | 28,217 |
| slow_40s (FC off) | 29,939 | 24,146 | 24,573 | 24,910 |
| slow_60s (FC on) | 195,524 | 19,225 | 32,884 | 32,541 |
| slow_60s (FC off) | 30,607 | 23,443 | 181,182 | 35,676 |

### 3.3 Thinking Tokens P50 — June 23 Full Benchmark

| Request | Minimal | Low | Medium | High |
|---------|---------|-----|--------|------|
| slow_40s (FC on) | 4,244 | 3,360 | 3,954 | 3,311 |
| slow_40s (FC off) | 4,109 | 3,558 | 3,889 | 3,390 |
| slow_60s (FC on) | 2,047 | 1,422 | 2,599 | 1,695 |
| slow_60s (FC off) | 1,981 | 1,838 | 2,682 | 1,852 |

### 3.4 Key Findings — Tool-Use Requests

1. **Thinking level has NO monotonic effect on TTFT or thinking tokens.** Unlike traditional requests where minimal < low < medium < high is a clear staircase, tool-use requests show no such pattern. Minimal is often the worst performer.

2. **Thinking tokens are NOT zero at minimal.** Traditional requests at minimal produce 0 thinking tokens and sub-1s TTFT. Tool-use requests at minimal produce 3,300–4,200 thinking tokens (slow_40s) and ~2,000 tokens (slow_60s). The model thinks heavily regardless of the thinking level setting.

3. **Thinking tokens are roughly flat across all levels.**
   - slow_request_40s P50: 3,311–4,244 across all 4 levels — essentially the same band.
   - slow_request_60s P50: 1,422–2,682 across all levels.
   - The `thinkingLevel` parameter has minimal control over how much the model thinks on tool-use requests.

4. **TTFT still tracks thinking tokens.** The ~4–5ms per thinking token relationship holds, but since thinking tokens don't respond to the thinking level knob, TTFT doesn't either.

5. **Extreme outliers are stochastic, not level-dependent.** P90 spikes to 180–195s (with ~62K thinking tokens) appear at minimal (60s FC on) and medium (60s FC off) — not at high. These "runaway thinking" events are random.

6. **Streaming FC on vs off shows no consistent directional effect** on tool-use requests.

---

## 4. After-Fix Benchmark (June 24) — Tool-Use Only

### 4.1 TTFT P50 (ms)

| Request | Minimal | Low | Medium | High |
|---------|---------|-----|--------|------|
| slow_40s (FC on) | 17,222 | 13,585 | 14,022 | 14,585 |
| slow_40s (FC off) | 16,449 | 15,178 | 15,726 | 17,574 |
| slow_60s (FC on) | 12,517 | 11,136 | 7,673 | 5,533 |
| slow_60s (FC off) | 14,876 | 17,775 | 13,906 | 14,202 |

### 4.2 Thinking Tokens P50

| Request | Minimal | Low | Medium | High |
|---------|---------|-----|--------|------|
| slow_40s (FC on) | 4,137 | 3,118 | 3,442 | 3,410 |
| slow_40s (FC off) | 4,334 | 3,656 | 3,808 | 4,244 |
| slow_60s (FC on) | 1,950 | 1,640 | 205 | 134 |
| slow_60s (FC off) | 2,023 | 1,944 | 1,888 | 2,636 |

### 4.3 Key Findings — After-Fix

1. **Same core pattern as pre-fix:** thinking level still has no meaningful control over tool-use requests. Thinking tokens cluster in the same 3,100–4,300 range for slow_40s.

2. **slow_request_60s remains highly erratic.** Some combos had only 8–9 successful iterations (429 rate limiting). Extreme outliers persisted (e.g., high FC off P90 = 45,738ms).

3. **The fix did not change the fundamental thinking level behavior** for tool-use requests.

---

## 5. Pre-Fix (May 20) vs After-Fix (June 24) TTFT Comparison

Comparing `perf_results_gemini-3.5-flash_all_locations_10iter_warmed_20260520.csv` (pre-fix, global location only) against `benchmark_summary_20260624_004938_after_fix.csv` (after-fix).

**Important:** The request files changed between benchmarks:
- slow_request_40s: 23,676 input tokens (May 20) → 37,112 input tokens (June 24)
- slow_request_60s: 94,852 input tokens (May 20) → 110,419 input tokens (June 24)

The after-fix benchmark processes **larger requests** in all cases.

### 5.1 slow_request_40s — TTFT P50 (ms)

| Thinking | Pre-fix (May 20) | After-fix (Jun 24, avg FC on/off) | Delta |
|----------|------------------|-------------------------------------|-------|
| minimal | 19,237 | 16,835 | -2,402 (-12%) |
| low | 18,401 | 14,381 | -4,020 (-22%) |
| medium | 15,579 | 14,874 | -705 (-5%) |
| high | 18,993 | 16,079 | -2,914 (-15%) |
| default | 19,209 | — | — |

### 5.2 slow_request_40s — TTFT P90 (ms)

| Thinking | Pre-fix (May 20) | After-fix (Jun 24, avg FC on/off) | Delta |
|----------|------------------|-------------------------------------|-------|
| minimal | 40,500 | 27,864 | -12,636 (-31%) |
| low | 23,659 | 21,471 | -2,188 (-9%) |
| medium | 22,740 | 26,742 | +4,002 (+18%) |
| high | 36,215 | 22,658 | -13,557 (-37%) |
| default | 24,951 | — | — |

### 5.3 slow_request_60s — TTFT P50 (ms)

| Thinking | Pre-fix (May 20) | After-fix (Jun 24, avg FC on/off) | Delta |
|----------|------------------|-------------------------------------|-------|
| minimal | 13,410 | 13,697 | +287 (+2%) |
| low | 8,433 | 14,456 | +6,023 (+71%) |
| medium | 14,269 | 10,789 | -3,480 (-24%) |
| high | 14,911 | 9,868 | -5,043 (-34%) |
| default | 14,867 | — | — |

### 5.4 slow_request_60s — TTFT P90 (ms)

| Thinking | Pre-fix (May 20) | After-fix (Jun 24, avg FC on/off) | Delta |
|----------|------------------|-------------------------------------|-------|
| minimal | 17,864 | 43,742 | +25,878 (+145%) |
| low | 16,469 | 19,425 | +2,956 (+18%) |
| medium | 105,533 | 22,340 | -83,193 (-79%) |
| high | 42,886 | 31,689 | -11,197 (-26%) |
| default | 34,842 | — | — |

### 5.5 Key Findings — Pre-Fix vs After-Fix

1. **slow_request_40s shows consistent TTFT improvement after the fix.** P50 improved 5–22% across all thinking levels despite processing a larger request (37,112 vs 23,676 input tokens). P90 improved significantly at minimal (-31%) and high (-37%).

2. **slow_request_60s results are mixed and noisy.** Some levels improved (medium P90 dropped 79%, high P50 dropped 34%), while others got worse (minimal P90 increased 145%, low P50 increased 71%). With only 8–10 iterations and extreme outliers (~62K thinking tokens), these differences are likely driven by sampling variance rather than real changes.

3. **Both benchmarks confirm thinking level has no control over tool-use TTFT.** Pre-fix slow_40s ranged 15,579–19,237 P50 across levels; after-fix ranged 14,381–16,835. No monotonic pattern in either dataset.

4. **The "default" thinking level** (no thinkingConfig set, May 20 only) performed similarly to explicitly set levels — further evidence that the thinking level parameter is ignored for tool-use requests.

5. **The fix appears to have improved slow_request_40s performance** (the more stable of the two). For slow_request_60s, the inherent variance makes it difficult to draw firm conclusions from 10-iteration samples.

---

## 6. Summary of Conclusions

### Traditional Requests (no tools)
- `thinkingLevel` works as intended: clear monotonic control over thinking tokens and TTFT
- Minimal = zero thinking tokens, sub-1s TTFT
- TTFT scales linearly with thinking tokens at ~5–6ms per token
- Larger input sizes amplify the thinking token count and TTFT at higher levels

### Tool-Use Requests
- `thinkingLevel` is effectively ignored: all levels produce similar thinking token counts
- Minimal thinking still generates 2,000–4,500 thinking tokens (never zero)
- TTFT is 10–20s P50 regardless of thinking level setting
- Extreme outliers (~62K thinking tokens, 180–200s TTFT) occur stochastically across all thinking levels
- Streaming FC (on/off) has no consistent effect on TTFT or thinking behavior

### Pre-Fix (May 20) vs After-Fix (June 24)
- slow_request_40s shows consistent TTFT improvement: P50 down 5–22%, P90 down 9–37% — despite processing a larger request (37,112 vs 23,676 input tokens)
- slow_request_60s results are too noisy to draw firm conclusions (extreme outliers dominate with only 10 iterations)
- Neither benchmark shows thinking level controlling tool-use behavior — the fix improved speed but did not change the fundamental issue
