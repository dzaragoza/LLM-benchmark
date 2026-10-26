# randomizer.md - the randomizer ledger

## the top 5% dashboard

- measured: 147 done candidates, top 7 (7 of 147)
- params median: **0.3403 B**
- model_quant mode: **Q2_K_S**
- k_quant mode: **f16**
- v_quant mode: **f16**
- score median: **-1**
- vulkan0 ram median: **3.87 GiB**
- context median: **1,048,576**

_the machine sweet-spot band, live as the pool fills_

Every candidate gets ONE chance (no replacement). Rank:
highest score, tiebreak by time. Speed: the candidate's
whole run - fast <= 32s, medium <= 64s, slow <= 128s.

| rank | model | high score | quant @high | k | v | vulkan0 ram | ctx | speed |
|---|---|---|---|---|---|---|---|---|
| 1 | granite-4.0-h-350m | -1 | Q2_K_S | f16 | f16 | 5.18 | 1,048,576 | fast |
| 2 | granite-4.0-h-350m | -1 | Q2_K_S | f16 | q8_0 | 4.25 | 1,048,576 | fast |
| 3 | granite-4.0-h-350m | -1 | Q2_K_S | f16 | q4_0 | 3.75 | 1,048,576 | fast |
| 4 | granite-4.0-h-350m | -1 | Q2_K_S | f16 | q4_1 | 3.81 | 1,048,576 | fast |
| 5 | granite-4.0-h-350m | -1 | Q2_K_S | f16 | iq4_nl | 3.75 | 1,048,576 | fast |
| 6 | granite-4.0-h-350m | -1 | Q2_K_S | f16 | q5_0 | 3.87 | 1,048,576 | fast |
| 7 | granite-4.0-h-350m | -1 | Q2_K_S | f16 | q5_1 | 3.94 | 1,048,576 | fast |
| 8 | granite-4.0-h-350m | -1 | Q2_K_S | q8_0 | f16 | 4.25 | 1,048,576 | fast |
| 9 | granite-4.0-h-350m | -1 | Q2_K_S | q8_0 | q8_0 | 3.31 | 1,048,576 | fast |
| 10 | granite-4.0-h-350m | -1 | Q2_K_S | q8_0 | q4_0 | 2.81 | 1,048,576 | fast |
| 11 | granite-4.0-h-350m | -1 | Q2_K_S | q8_0 | q4_1 | 2.87 | 1,048,576 | fast |
| 12 | granite-4.0-h-350m | -1 | Q2_K_S | q8_0 | iq4_nl | 2.81 | 1,048,576 | fast |
| 13 | granite-4.0-h-350m | -1 | Q2_K_S | q8_0 | q5_0 | 2.94 | 1,048,576 | fast |
| 14 | granite-4.0-h-350m | -1 | Q2_K_S | q8_0 | q5_1 | 3.00 | 1,048,576 | fast |
| 15 | granite-4.0-h-350m | -1 | Q2_K_S | q4_0 | f16 | 3.75 | 1,048,576 | fast |
| 16 | granite-4.0-h-350m | -1 | Q2_K_S | q4_0 | q8_0 | 2.81 | 1,048,576 | fast |
| 17 | granite-4.0-h-350m | -1 | Q2_K_S | q4_0 | q4_0 | 2.31 | 1,048,576 | fast |
| 18 | granite-4.0-h-350m | -1 | Q2_K_S | q4_0 | q4_1 | 2.37 | 1,048,576 | fast |
| 19 | granite-4.0-h-350m | -1 | Q2_K_S | q4_0 | iq4_nl | 2.31 | 1,048,576 | fast |
| 20 | granite-4.0-h-350m | -1 | Q2_K_S | q4_0 | q5_0 | 2.44 | 1,048,576 | fast |
| 21 | granite-4.0-h-350m | -1 | Q2_K_S | q4_0 | q5_1 | 2.50 | 1,048,576 | fast |
| 22 | granite-4.0-h-350m | -1 | Q2_K_S | q4_1 | f16 | 3.81 | 1,048,576 | fast |
| 23 | granite-4.0-h-350m | -1 | Q2_K_S | q4_1 | q8_0 | 2.87 | 1,048,576 | fast |
| 24 | granite-4.0-h-350m | -1 | Q2_K_S | q4_1 | q4_0 | 2.37 | 1,048,576 | fast |
| 25 | granite-4.0-h-350m | -1 | Q2_K_S | q4_1 | q4_1 | 2.44 | 1,048,576 | fast |
| 26 | granite-4.0-h-350m | -1 | Q2_K_S | q4_1 | iq4_nl | 2.37 | 1,048,576 | fast |
| 27 | granite-4.0-h-350m | -1 | Q2_K_S | q4_1 | q5_0 | 2.50 | 1,048,576 | fast |
| 28 | granite-4.0-h-350m | -1 | Q2_K_S | q4_1 | q5_1 | 2.56 | 1,048,576 | fast |
| 29 | granite-4.0-h-350m | -1 | Q2_K_S | iq4_nl | f16 | 3.75 | 1,048,576 | fast |
| 30 | granite-4.0-h-350m | -1 | Q2_K_S | iq4_nl | q8_0 | 2.81 | 1,048,576 | fast |
| 31 | granite-4.0-h-350m | -1 | Q2_K_S | iq4_nl | q4_0 | 2.31 | 1,048,576 | fast |
| 32 | granite-4.0-h-350m | -1 | Q2_K_S | iq4_nl | q4_1 | 2.37 | 1,048,576 | fast |
| 33 | granite-4.0-h-350m | -1 | Q2_K_S | iq4_nl | iq4_nl | 2.31 | 1,048,576 | fast |
| 34 | granite-4.0-h-350m | -1 | Q2_K_S | iq4_nl | q5_0 | 2.44 | 1,048,576 | fast |
| 35 | granite-4.0-h-350m | -1 | Q2_K_S | iq4_nl | q5_1 | 2.50 | 1,048,576 | fast |
| 36 | granite-4.0-h-350m | -1 | Q2_K_S | q5_0 | f16 | 3.87 | 1,048,576 | fast |
| 37 | granite-4.0-h-350m | -1 | Q2_K_S | q5_0 | q8_0 | 2.94 | 1,048,576 | fast |
| 38 | granite-4.0-h-350m | -1 | Q2_K_S | q5_0 | q4_0 | 2.44 | 1,048,576 | fast |
| 39 | granite-4.0-h-350m | -1 | Q2_K_S | q5_0 | q4_1 | 2.50 | 1,048,576 | fast |
| 40 | granite-4.0-h-350m | -1 | Q2_K_S | q5_0 | iq4_nl | 2.44 | 1,048,576 | fast |
| 41 | granite-4.0-h-350m | -1 | Q2_K_S | q5_0 | q5_0 | 2.56 | 1,048,576 | fast |
| 42 | granite-4.0-h-350m | -1 | Q2_K_S | q5_0 | q5_1 | 2.62 | 1,048,576 | fast |
| 43 | granite-4.0-h-350m | -1 | Q2_K_S | q5_1 | f16 | 3.94 | 1,048,576 | fast |
| 44 | granite-4.0-h-350m | -1 | Q2_K_S | q5_1 | q8_0 | 3.00 | 1,048,576 | fast |
| 45 | granite-4.0-h-350m | -1 | Q2_K_S | q5_1 | q4_0 | 2.50 | 1,048,576 | fast |
| 46 | granite-4.0-h-350m | -1 | Q2_K_S | q5_1 | q4_1 | 2.56 | 1,048,576 | fast |
| 47 | granite-4.0-h-350m | -1 | Q2_K_S | q5_1 | iq4_nl | 2.50 | 1,048,576 | fast |
| 48 | granite-4.0-h-350m | -1 | Q2_K_S | q5_1 | q5_0 | 2.62 | 1,048,576 | fast |
| 49 | granite-4.0-h-350m | -1 | Q2_K_S | q5_1 | q5_1 | 2.69 | 1,048,576 | fast |
| 50 | MiniCPM5-1B | -1 | Q3_K_L | f16 | f16 | 3.65 | 131,072 | slow |
| 51 | MiniCPM5-1B | -1 | Q3_K_L | f16 | q8_0 | 2.94 | 131,072 | slow |
| 52 | MiniCPM5-1B | -1 | Q3_K_L | f16 | q4_0 | 2.56 | 131,072 | slow |
| 53 | MiniCPM5-1B | -1 | Q3_K_L | f16 | q4_1 | 2.61 | 131,072 | slow |
| 54 | MiniCPM5-1B | -1 | Q3_K_L | f16 | iq4_nl | 2.56 | 131,072 | slow |
| 55 | MiniCPM5-1B | -1 | Q3_K_L | f16 | q5_0 | 2.66 | 131,072 | slow |
| 56 | MiniCPM5-1B | -1 | Q3_K_L | f16 | q5_1 | 2.71 | 131,072 | slow |
| 57 | MiniCPM5-1B | -1 | Q3_K_L | q8_0 | f16 | 2.94 | 131,072 | slow |
| 58 | MiniCPM5-1B | -1 | Q3_K_L | q8_0 | q8_0 | 2.24 | 131,072 | slow |
| 59 | MiniCPM5-1B | -1 | Q3_K_L | q8_0 | q4_0 | 1.87 | 131,072 | slow |
| 60 | MiniCPM5-1B | -1 | Q3_K_L | q8_0 | q4_1 | 1.92 | 131,072 | slow |
| 61 | MiniCPM5-1B | -1 | Q3_K_L | q8_0 | iq4_nl | 1.87 | 131,072 | slow |
| 62 | MiniCPM5-1B | -1 | Q3_K_L | q8_0 | q5_0 | 1.96 | 131,072 | slow |
| 63 | MiniCPM5-1B | -1 | Q3_K_L | q8_0 | q5_1 | 2.01 | 131,072 | slow |
| 64 | MiniCPM5-1B | -1 | Q3_K_L | q4_0 | f16 | 2.56 | 131,072 | slow |
| 65 | MiniCPM5-1B | -1 | Q3_K_L | q4_0 | q8_0 | 1.87 | 131,072 | slow |
| 66 | MiniCPM5-1B | -1 | Q3_K_L | q4_0 | q4_0 | 1.49 | 131,072 | slow |
| 67 | MiniCPM5-1B | -1 | Q3_K_L | q4_0 | q4_1 | 1.54 | 131,072 | slow |
| 68 | MiniCPM5-1B | -1 | Q3_K_L | q4_0 | iq4_nl | 1.49 | 131,072 | slow |
| 69 | MiniCPM5-1B | -1 | Q3_K_L | q4_0 | q5_0 | 1.59 | 131,072 | slow |
| 70 | MiniCPM5-1B | -1 | Q3_K_L | q4_0 | q5_1 | 1.63 | 131,072 | slow |
| 71 | MiniCPM5-1B | -1 | Q3_K_L | q4_1 | f16 | 2.61 | 131,072 | slow |
| 72 | MiniCPM5-1B | -1 | Q3_K_L | q4_1 | q8_0 | 1.92 | 131,072 | slow |
| 73 | MiniCPM5-1B | -1 | Q3_K_L | q4_1 | q4_0 | 1.54 | 131,072 | slow |
| 74 | MiniCPM5-1B | -1 | Q3_K_L | q4_1 | q4_1 | 1.59 | 131,072 | slow |
| 75 | MiniCPM5-1B | -1 | Q3_K_L | q4_1 | iq4_nl | 1.54 | 131,072 | slow |
| 76 | MiniCPM5-1B | -1 | Q3_K_L | q4_1 | q5_0 | 1.63 | 131,072 | slow |
| 77 | MiniCPM5-1B | -1 | Q3_K_L | q4_1 | q5_1 | 1.68 | 131,072 | slow |
| 78 | MiniCPM5-1B | -1 | Q3_K_L | iq4_nl | f16 | 2.56 | 131,072 | slow |
| 79 | MiniCPM5-1B | -1 | Q3_K_L | iq4_nl | q8_0 | 1.87 | 131,072 | slow |
| 80 | MiniCPM5-1B | -1 | Q3_K_L | iq4_nl | q4_0 | 1.49 | 131,072 | slow |
| 81 | MiniCPM5-1B | -1 | Q3_K_L | iq4_nl | q4_1 | 1.54 | 131,072 | slow |
| 82 | MiniCPM5-1B | -1 | Q3_K_L | iq4_nl | iq4_nl | 1.49 | 131,072 | slow |
| 83 | MiniCPM5-1B | -1 | Q3_K_L | iq4_nl | q5_0 | 1.59 | 131,072 | slow |
| 84 | MiniCPM5-1B | -1 | Q3_K_L | iq4_nl | q5_1 | 1.63 | 131,072 | slow |
| 85 | MiniCPM5-1B | -1 | Q3_K_L | q5_0 | f16 | 2.66 | 131,072 | slow |
| 86 | MiniCPM5-1B | -1 | Q3_K_L | q5_0 | q8_0 | 1.96 | 131,072 | slow |
| 87 | MiniCPM5-1B | -1 | Q3_K_L | q5_0 | q4_0 | 1.59 | 131,072 | slow |
| 88 | MiniCPM5-1B | -1 | Q3_K_L | q5_0 | q4_1 | 1.63 | 131,072 | slow |
| 89 | MiniCPM5-1B | -1 | Q3_K_L | q5_0 | iq4_nl | 1.59 | 131,072 | slow |
| 90 | MiniCPM5-1B | -1 | Q3_K_L | q5_0 | q5_0 | 1.68 | 131,072 | slow |
| 91 | MiniCPM5-1B | -1 | Q3_K_L | q5_0 | q5_1 | 1.73 | 131,072 | slow |
| 92 | MiniCPM5-1B | -1 | Q3_K_L | q5_1 | f16 | 2.71 | 131,072 | slow |
| 93 | MiniCPM5-1B | -1 | Q3_K_L | q5_1 | q8_0 | 2.01 | 131,072 | slow |
| 94 | MiniCPM5-1B | -1 | Q3_K_L | q5_1 | q4_0 | 1.63 | 131,072 | slow |
| 95 | MiniCPM5-1B | -1 | Q3_K_L | q5_1 | q4_1 | 1.68 | 131,072 | slow |
| 96 | MiniCPM5-1B | -1 | Q3_K_L | q5_1 | iq4_nl | 1.63 | 131,072 | slow |
| 97 | MiniCPM5-1B | -1 | Q3_K_L | q5_1 | q5_0 | 1.73 | 131,072 | slow |
| 98 | MiniCPM5-1B | -1 | Q3_K_L | q5_1 | q5_1 | 1.77 | 131,072 | slow |
| 99 | granite-3.1-2b-instruct | -1 | IQ1_S | f16 | f16 | 10.73 | 131,072 | slow |
| 100 | granite-3.1-2b-instruct | -1 | IQ1_S | f16 | q8_0 | 8.39 | 131,072 | slow |
| 101 | granite-3.1-2b-instruct | -1 | IQ1_S | f16 | q4_0 | 7.14 | 131,072 | slow |
| 102 | granite-3.1-2b-instruct | -1 | IQ1_S | f16 | q4_1 | 7.29 | 131,072 | slow |
| 103 | granite-3.1-2b-instruct | -1 | IQ1_S | f16 | iq4_nl | 7.14 | 131,072 | slow |
| 104 | granite-3.1-2b-instruct | -1 | IQ1_S | f16 | q5_0 | 7.45 | 131,072 | slow |
| 105 | granite-3.1-2b-instruct | -1 | IQ1_S | f16 | q5_1 | 7.61 | 131,072 | slow |
| 106 | granite-3.1-2b-instruct | -1 | IQ1_S | q8_0 | f16 | 8.39 | 131,072 | slow |
| 107 | granite-3.1-2b-instruct | -1 | IQ1_S | q8_0 | q8_0 | 6.04 | 131,072 | slow |
| 108 | granite-3.1-2b-instruct | -1 | IQ1_S | q8_0 | q4_0 | 4.79 | 131,072 | slow |
| 109 | granite-3.1-2b-instruct | -1 | IQ1_S | q8_0 | q4_1 | 4.95 | 131,072 | slow |
| 110 | granite-3.1-2b-instruct | -1 | IQ1_S | q8_0 | iq4_nl | 4.79 | 131,072 | slow |
| 111 | granite-3.1-2b-instruct | -1 | IQ1_S | q8_0 | q5_0 | 5.11 | 131,072 | slow |
| 112 | granite-3.1-2b-instruct | -1 | IQ1_S | q8_0 | q5_1 | 5.26 | 131,072 | slow |
| 113 | granite-3.1-2b-instruct | -1 | IQ1_S | q4_0 | f16 | 7.14 | 131,072 | slow |
| 114 | granite-3.1-2b-instruct | -1 | IQ1_S | q4_0 | q8_0 | 4.79 | 131,072 | slow |
| 115 | granite-3.1-2b-instruct | -1 | IQ1_S | q4_0 | q4_0 | 3.54 | 131,072 | slow |
| 116 | granite-3.1-2b-instruct | -1 | IQ1_S | q4_0 | q4_1 | 3.70 | 131,072 | slow |
| 117 | granite-3.1-2b-instruct | -1 | IQ1_S | q4_0 | iq4_nl | 3.54 | 131,072 | slow |
| 118 | granite-3.1-2b-instruct | -1 | IQ1_S | q4_0 | q5_0 | 3.85 | 131,072 | slow |
| 119 | granite-3.1-2b-instruct | -1 | IQ1_S | q4_0 | q5_1 | 4.01 | 131,072 | slow |
| 120 | granite-3.1-2b-instruct | -1 | IQ1_S | q4_1 | f16 | 7.29 | 131,072 | slow |
| 121 | granite-3.1-2b-instruct | -1 | IQ1_S | q4_1 | q8_0 | 4.95 | 131,072 | slow |
| 122 | granite-3.1-2b-instruct | -1 | IQ1_S | q4_1 | q4_0 | 3.70 | 131,072 | slow |
| 123 | granite-3.1-2b-instruct | -1 | IQ1_S | q4_1 | q4_1 | 3.85 | 131,072 | slow |
| 124 | granite-3.1-2b-instruct | -1 | IQ1_S | q4_1 | iq4_nl | 3.70 | 131,072 | slow |
| 125 | granite-3.1-2b-instruct | -1 | IQ1_S | q4_1 | q5_0 | 4.01 | 131,072 | slow |
| 126 | granite-3.1-2b-instruct | -1 | IQ1_S | q4_1 | q5_1 | 4.17 | 131,072 | slow |
| 127 | granite-3.1-2b-instruct | -1 | IQ1_S | iq4_nl | f16 | 7.14 | 131,072 | slow |
| 128 | granite-3.1-2b-instruct | -1 | IQ1_S | iq4_nl | q8_0 | 4.79 | 131,072 | slow |
| 129 | granite-3.1-2b-instruct | -1 | IQ1_S | iq4_nl | q4_0 | 3.54 | 131,072 | slow |
| 130 | granite-3.1-2b-instruct | -1 | IQ1_S | iq4_nl | q4_1 | 3.70 | 131,072 | slow |
| 131 | granite-3.1-2b-instruct | -1 | IQ1_S | iq4_nl | iq4_nl | 3.54 | 131,072 | slow |
| 132 | granite-3.1-2b-instruct | -1 | IQ1_S | iq4_nl | q5_0 | 3.85 | 131,072 | slow |
| 133 | granite-3.1-2b-instruct | -1 | IQ1_S | iq4_nl | q5_1 | 4.01 | 131,072 | slow |
| 134 | granite-3.1-2b-instruct | -1 | IQ1_S | q5_0 | f16 | 7.45 | 131,072 | slow |
| 135 | granite-3.1-2b-instruct | -1 | IQ1_S | q5_0 | q8_0 | 5.11 | 131,072 | slow |
| 136 | granite-3.1-2b-instruct | -1 | IQ1_S | q5_0 | q4_0 | 3.85 | 131,072 | slow |
| 137 | granite-3.1-2b-instruct | -1 | IQ1_S | q5_0 | q4_1 | 4.01 | 131,072 | slow |
| 138 | granite-3.1-2b-instruct | -1 | IQ1_S | q5_0 | iq4_nl | 3.85 | 131,072 | slow |
| 139 | granite-3.1-2b-instruct | -1 | IQ1_S | q5_0 | q5_0 | 4.17 | 131,072 | slow |
| 140 | granite-3.1-2b-instruct | -1 | IQ1_S | q5_0 | q5_1 | 4.32 | 131,072 | slow |
| 141 | granite-3.1-2b-instruct | -1 | IQ1_S | q5_1 | f16 | 7.61 | 131,072 | slow |
| 142 | granite-3.1-2b-instruct | -1 | IQ1_S | q5_1 | q8_0 | 5.26 | 131,072 | slow |
| 143 | granite-3.1-2b-instruct | -1 | IQ1_S | q5_1 | q4_0 | 4.01 | 131,072 | slow |
| 144 | granite-3.1-2b-instruct | -1 | IQ1_S | q5_1 | q4_1 | 4.17 | 131,072 | slow |
| 145 | granite-3.1-2b-instruct | -1 | IQ1_S | q5_1 | iq4_nl | 4.01 | 131,072 | slow |
| 146 | granite-3.1-2b-instruct | -1 | IQ1_S | q5_1 | q5_0 | 4.32 | 131,072 | slow |
| 147 | granite-3.1-2b-instruct | -1 | IQ1_S | q5_1 | q5_1 | 4.48 | 131,072 | slow |

_147 candidates run of 100,352 (4 of 2,048 pairs swept); each pair one acquisition, the seed recorded in state._
