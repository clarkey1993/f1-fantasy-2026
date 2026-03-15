# Pat Collins – Constructor Scoring Audit (Australia 2026)

## Per-constructor breakdown

| Team (pick) | Drivers | Statuses | Finishers | Finisher bonus | Constructor rank | Finish pts | Deductions | Total |
|-------------|---------|----------|-----------|----------------|-------------------|------------|------------|-------|
| **Ferrari** | LEC, HAM | LEC=Finished, HAM=Finished | 2 | 20 | 2 | 18 | 0 | **38** |
| **McLaren** | NOR, PIA | NOR=Finished, PIA=Did not start | 1 | 10 | 3 | 15 | 0 | **25** |
| **Red Bull** | VER, HAD | VER=Finished, HAD=Retired | 1 | 10 | 4 | 12 | 0 | **22** |
| **Alpine** | GAS, COL | GAS=Lapped, COL=Lapped | 2 | 20 | 8 | 4 | 0 | **24** |
| **Audi** | BOR, HUL | BOR=Lapped, HUL=Did not start | 1 | 10 | 7 | 6 | 0 | **16** |
| **Cadillac** | PER, BOT | PER=Lapped, BOT=Retired | 1 | 10 | 10 | 1 | 0 | **11** |

**Constructor total: 136**

---

## Rules check

- **10 points per finisher:** Applied to classified finishers only (Finished or Lapped).  
- **Constructor rank finish points:** Taken from rank map (1=25, 2=18, 3=15, 4=12, 5=10, 6=8, 7=6, 8=4, 9=2, 10=1).  
- **−10 for DSQ:** No Disqualified/Excluded in these teams; deductions = 0.

---

## Retired / DNS handling

| Constructor | Non-finisher | Status | Counted as finisher? | Correct? |
|-------------|--------------|--------|----------------------|----------|
| McLaren | PIA | Did not start | No | Yes |
| Red Bull | HAD | Retired | No | Yes |
| Audi | HUL | Did not start | No | Yes |
| Cadillac | BOT | Retired | No | Yes |

- **Retired (HAD, BOT):** Not classified; `_finished()` is False; not in finishers list; no finisher bonus.  
- **Did not start (PIA, HUL):** Same; no finisher bonus.

---

## Finisher counting

- **Ferrari:** LEC, HAM both Finished → 2 finishers, 20 pts.  
- **McLaren:** NOR Finished, PIA DNS → 1 finisher, 10 pts.  
- **Red Bull:** VER Finished, HAD Retired → 1 finisher, 10 pts.  
- **Alpine:** GAS, COL both Lapped (classified) → 2 finishers, 20 pts.  
- **Audi:** BOR Lapped, HUL DNS → 1 finisher, 10 pts.  
- **Cadillac:** PER Lapped, BOT Retired → 1 finisher, 10 pts.

No finisher is counted incorrectly.

---

## Constructor rank

Rank map (Australia 2026, classified finishers only):

1. Mercedes 25  
2. Ferrari 18  
3. McLaren 15  
4. Red Bull Racing 12  
5. Haas F1 Team 10  
6. Racing Bulls 8  
7. Audi 6  
8. Alpine 4  
9. Williams 2  
10. Cadillac 1  

Aston Martin (both cars retired) has no finishers and is not in the map.

Pat’s teams use ranks 2, 3, 4, 8, 7, 10 and the corresponding finish points (18, 15, 12, 4, 6, 1). No rank mismatch.

---

## Verdict

- Retired drivers (HAD, BOT) are not treated as finishers.  
- DNS (PIA, HUL) are not treated as finishers.  
- Lapped classified drivers (GAS, COL, BOR, PER) are correctly treated as finishers.  
- Finisher bonus, constructor rank finish points, and DSQ deductions match the rules.  
- **Pat Collins’ constructor scoring for Australia 2026 is correct.**
