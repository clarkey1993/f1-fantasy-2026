# Mark Shaw Australia 2026 – Targeted Audit

**Team:** Charles Leclerc, George Russell, Kimi Antonelli, Lewis Hamilton, Isack Hadjar, Alex Albon, Liam Lawson, Nico Hulkenberg, Gabriel Bortoleto, Sergio Perez | Ferrari, Mercedes, Red Bull, Alpine, Audi, Racing Bulls

**App score:** 845  
**Manual score:** 863  
**Gap:** 18 points

---

## 1. Full Manual Breakdown (Per Written Rules)

### Written Rules (signup.html)
- **Grid:** 20 for P1 … 1 for P20 (fantasy grid after DNS/pit-lane shifts)
- **Laps:** 1 pt per lap completed
- **Improvement:** 1 pt per position gained (grid → finish)
- **Finishing:** Only if driver takes chequered flag (Finished / Lapped)
- **Fastest Lap:** 25 pts
- **Constructors:** 10 pts per finishing car + constructor finishing points by rank (25,18,15,12,10,8,6,4,2,1 for ranks 1–10)

### DNS and Grid Adjustments
- **DNS:** Hulkenberg (HUL), Piastri (PIA)  
- DNS drivers are removed from the grid; everyone else is renumbered 1–20 (fantasy grid).

### Driver Breakdown

| Driver | Orig Grid | Fantasy Grid | Laps | Status | Finish | Grid Pts | Lap Pts | Gain | Finish Pts | Fastest | Total |
|--------|-----------|--------------|------|--------|--------|----------|---------|------|------------|---------|-------|
| Charles Leclerc | 4 | 4 | 58 | Finished | 3 | 17 | 58 | 1 | 15 | 0 | 91 |
| George Russell | 1 | 1 | 58 | Finished | 1 | 20 | 58 | 0 | 25 | 0 | 103 |
| Kimi Antonelli | 2 | 2 | 58 | Finished | 2 | 19 | 58 | 0 | 18 | 0 | 95 |
| Lewis Hamilton | 7 | 6 | 58 | Finished | 4 | 15 | 58 | 2 | 12 | 0 | 87 |
| Isack Hadjar | 3 | 3 | 10 | Retired | - | 18 | 10 | 0 | 0 | 0 | 28 |
| Alex Albon | 15 | 13 | 57 | Lapped | 12 | 8 | 57 | 1 | 0 | 0 | 66 |
| Liam Lawson | 8 | 7 | 57 | Lapped | 13 | 14 | 57 | 0 | 0 | 0 | 71 |
| **Nico Hulkenberg** | 11 | - | 0 | **DNS** | - | **0** | **0** | 0 | 0 | 0 | **0** |
| Gabriel Bortoleto | 10 | 9 | 57 | Lapped | 9 | 12 | 57 | 0 | 2 | 0 | 71 |
| Sergio Perez | 18 | 16 | 55 | Lapped | 16 | 5 | 55 | 0 | 0 | 0 | 60 |

**Driver total:** 672

**Notes:**
- HAM: PIA (orig 5) and HUL (orig 11) DNS → HAM’s fantasy grid = 6 (not 7).
- HUL: DNS → 0 points.
- BOR: P9 → 2 pts.
- Fastest lap: VER (not in Mark’s team) → 0 pts.

### Constructor Breakdown

| Constructor | Finishers | Best Car | Constr Rank | Finisher Bonus | Rank Pts | Total |
|-------------|-----------|----------|-------------|----------------|----------|-------|
| Ferrari | 2 (LEC, HAM) | P3 | 2 | 20 | 18 | 38 |
| Mercedes | 2 (RUS, ANT) | P1 | 1 | 20 | 25 | 45 |
| Red Bull | 1 (VER; HAD retired) | P6 | 4 | 10 | 12 | 22 |
| Alpine | 2 | P10 | 8 | 20 | 4 | 24 |
| Audi | 1 (BOR; HUL DNS) | P9 | 7 | 10 | 6 | 16 |
| Racing Bulls | 2 | P8 | 6 | 20 | 8 | 28 |

**Constructor total:** 173

**Constructor rank map (Australia 2026):**
1. Mercedes 25 | 2. Ferrari 18 | 3. McLaren 15 | 4. Red Bull 12 | 5. Haas 10 | 6. Racing Bulls 8 | 7. Audi 6 | 8. Alpine 4 | 9. Williams 2 | 10. Cadillac 1 | 11. Aston Martin 0

---

## 2. Exact Source of the 18-Point Gap

**845 (correct) − 863 (manual) = −18**

The only way to get an extra 18 points is to award points where the rules give 0.

**Most plausible cause: Nico Hulkenberg (DNS) given 18 points**

- **Rules:** DNS = no grid, laps, gain, finish, or fastest lap → **0 points**.
- **App:** HUL = 0 ✓  
- **Manual error:** If HUL is given 18 pts (e.g. grid as if he started P3: 21−3=18, or some laps/grid combo), that would explain the full gap.

**Alternative (unlikely):**

- Extra constructor points, wrong grid shifts, or laps miscount could also sum to 18, but the HUL hypothesis fits the exact 18-point difference most simply.

---

## 3. Verdict

**Correct total under the league rules: 845**

- Driver total: 672  
- Constructor total: 173  
- Grand total: **845**

**Why the manual score of 863 is inconsistent with the written rules**

- The manual total is 18 points too high.
- The most straightforward explanation is that **Nico Hulkenberg (DNS)** was incorrectly awarded points (likely 18 grid points) despite not starting.
- Per the rules, a DNS driver receives 0 points, so the app’s treatment of Hulkenberg is correct and the manual score should be reduced by 18 points.
