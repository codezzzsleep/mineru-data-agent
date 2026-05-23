# Financial Table Human Spot Check

Scope: one synthetic financial PDF fixture, table `Line Item / 2024 Q1..FY 2024`.

Boundary: this is a sample-level human arithmetic check for the fixture table. It is not a general field-level accuracy benchmark and is not an accounting audit opinion.

| Check | Extracted values | Expected | Result |
| --- | --- | ---: | --- |
| Product revenue FY 2024 | 55,350 | 55,350 | match |
| Service revenue FY 2024 | 23,070 | 23,070 | match |
| R&D expense FY 2024 | -13,560 | -13,560 | match |
| Q1 operating result | 12,340 + 5,220 - 740 - 3,180 - 2,280 - 3,100 - 1,420 - 260 | 6,580 | match |
| Q2 operating result | 13,110 + 5,480 - 810 - 3,440 - 2,440 - 3,260 - 1,500 - 280 | 6,860 | match |
| Q3 operating result | 14,220 + 6,040 - 860 - 3,720 - 2,510 - 3,490 - 1,605 - 310 | 7,765 | match |
| Q4 operating result | 15,680 + 6,330 - 910 - 3,990 - 2,690 - 3,710 - 1,710 - 330 | 8,670 | match |
| FY operating result | 55,350 + 23,070 - 3,320 - 14,330 - 9,920 - 13,560 - 6,235 - 1,180 | 29,875 | match |

Sample numerator/denominator: 8 / 8 checked values matched the fixture expectation.
