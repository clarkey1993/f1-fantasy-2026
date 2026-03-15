# ±1 Point Mismatch Audit – Australia 2026

## Summary

| Player | App | Manual | Diff | Verdict |
|--------|-----|--------|------|---------|
| Andy Coates | 940 | 941 | -1 | **App correct** |
| Stuart Pollard | 877 | 876 | +1 | **App correct** |
| Peter Wright | 857 | 856 | +1 | **App correct** |
| Tony Hewitt | 857 | 856 | +1 | **App correct** |
| Nathan Houghton | 847 | 846 | +1 | **App correct** |
| Jack Reynolds | 825 | 824 | +1 | **App correct** |
| Joel Adderley | 815 | 814 | +1 | **App correct** |

---

## 1. Andy Coates (app 940 vs manual 941)

**Difference:** Manual +1

**Full app breakdown (Australia 2026):**
- Drivers: RUS 103, VER 106, ANT 95, HAM 87, HAD 28, ALB 66, LAW 71, LIN 74, COL 63, PER 60 → **753**
- Constructors: Ferrari 38, Mercedes 45, Red Bull 22, Alpine 24, Haas 30, Racing Bulls 28 → **187**
- **Total: 940**

**Likely source of +1:** Manual scorer likely gave **1 extra lap point** to a driver. Franco Colapinto (COL) has 56 laps (FastF1 and app); if manual used 57, that would add +1.

**Verdict:** **App correct.** Rules: “1 point for every lap completed.” App uses FastF1 lap counts. Manual appears to have added one lap point in error.

---

## 2. Stuart Pollard (app 877 vs manual 876)

**Difference:** Manual -1

**Full app breakdown:**
- Drivers: RUS 103, VER 106, ANT 95, HAM 87, SAI 62, ALB 66, OCO 67, HUL 0 (DNS), COL 63, PER 60 → **709**
- Constructors: Ferrari 38, Mercedes 45, Red Bull 22, Williams 22, Haas 30, Cadillac 11 → **168**
- **Total: 877**

**Likely source of -1:** Manual scorer likely used **56 laps instead of 57** for one driver (e.g. Esteban Ocon, Alex Albon, Liam Lawson), or **55 instead of 56** for Franco Colapinto or Carlos Sainz. FastF1: COL 56, SAI 56, OCO 57, ALB 57. One lap undercount explains -1.

**Verdict:** **App correct.** Manual is missing one lap point.

---

## 3. Peter Wright (app 857 vs manual 856)

**Difference:** Manual -1

**Full app breakdown:**
- Drivers: LEC 91, RUS 103, ANT 95, HAM 87, HAD 28, ALB 66, BEA 77, HUL 0, COL 63, PER 60 → **670**
- Constructors: Ferrari 38, Mercedes 45, Red Bull 22, Alpine 24, Haas 30, Racing Bulls 28 → **187**
- **Total: 857**

**Likely source of -1:** Franco Colapinto has 56 laps. If manual used 55 laps, that would give -1.

**Verdict:** **App correct.** Manual missing one lap point for Colapinto.

---

## 4. Tony Hewitt (app 857 vs manual 856)

**Difference:** Manual -1

**Full app breakdown:**
- Drivers: LEC 91, RUS 103, ANT 95, HAM 87, GAS 69, ALB 66, BEA 77, HUL 0, COL 63, BOT 19 → **670**
- Constructors: Ferrari 38, Mercedes 45, Red Bull 22, Alpine 24, Haas 30, Racing Bulls 28 → **187**
- **Total: 857**

**Likely source of -1:** Same as Peter Wright: Colapinto 56 laps; manual likely used 55.

**Verdict:** **App correct.** Manual missing one lap point for Colapinto.

---

## 5. Nathan Houghton (app 847 vs manual 846)

**Difference:** Manual -1

**Full app breakdown:**
- Drivers: LEC 91, VER 106, ANT 95, PIA 0 (DNS), GAS 69, ALB 66, BEA 77, LIN 74, COL 63, BOT 19 → **660**
- Constructors: Ferrari 38, Mercedes 45, Red Bull 22, Alpine 24, Haas 30, Racing Bulls 28 → **187**
- **Total: 847**

**Likely source of -1:** Colapinto 56 laps; manual likely used 55 laps.

**Verdict:** **App correct.** Manual missing one lap point.

---

## 6. Jack Reynolds (app 825 vs manual 824)

**Difference:** Manual -1

**Full app breakdown:**
- Drivers: LEC 91, NOR 84, HAM 87, ANT 95, GAS 69, ALB 66, BEA 77, HUL 0, COL 63, BOT 19 → **651**
- Constructors: Mercedes 45, McLaren 25, Red Bull 22, Alpine 24, Haas 30, Racing Bulls 28 → **174**
- **Total: 825**

**Likely source of -1:** Colapinto 56 laps; manual likely used 55 laps.

**Verdict:** **App correct.** Manual missing one lap point.

---

## 7. Joel Adderley (app 815 vs manual 814)

**Difference:** Manual -1

**Full app breakdown:**
- Drivers: RUS 103, NOR 84, ANT 95, PIA 0, SAI 62, ALB 66, BEA 77, LIN 74, COL 63, BOT 19 → **643**
- Constructors: McLaren 25, Mercedes 45, Red Bull 22, Williams 22, Haas 30, Racing Bulls 28 → **172**
- **Total: 815**

**Likely source of -1:** Colapinto 56 laps; manual likely used 55 laps. Alternatively, Carlos Sainz 56 laps vs 55.

**Verdict:** **App correct.** Manual missing one lap point.

---

## Conclusion

1. **App logic is internally consistent** with the written rules.
2. **All 7 discrepancies** are most plausibly from **lap counts** for lapped finishers.
3. **App is correct in all cases.** The app uses FastF1 lap data; rules say “1 point for every lap completed.”
4. **Franco Colapinto (56 laps)** appears in all seven lineups; the manual scorer likely used **55 laps** for him in six cases (giving -1) and **57 laps** for Andy Coates (giving +1). Alternative: a different driver’s lap count differs by 1 in the manual calculation.
5. **Other components** (fantasy grid after DNS, gain points, finish points, constructor rank points) are consistent and give no sign of a systematic 1‑point error.
