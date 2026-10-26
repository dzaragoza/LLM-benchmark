# randomizer.md - the randomizer ledger

## the top 5% dashboard

- measured: 196 done candidates, top 9 (9 of 196)
- params median: **2.614 B**
- model_quant mode: **IQ4_NL**
- k_quant mode: **q8_0**
- v_quant mode: **q4_1**
- high-score level time median: **8.9s**
- score median: **2**
- vulkan0 ram median: **1.88 GiB**
- context median: **8,192**

_the machine sweet-spot band, live as the pool fills_

Every candidate gets ONE chance (no replacement). Rank:
highest score, tiebreak by time. Speed: the candidate's
whole run - fast <= 32s, medium <= 64s, slow <= 128s.

| rank | model | high score | quant @high | k | v | vulkan0 ram | ctx | speed |
|---|---|---|---|---|---|---|---|---|
| 1 | gemma-2-2b-it | 3 | IQ4_NL | f16 | q5_1 | 2.03 | 8,192 | fast |
| 2 | gemma-2-2b-it | 3 | IQ4_NL | q5_1 | q4_1 | 1.82 | 8,192 | fast |
| 3 | gemma-2-2b-it | 3 | IQ4_NL | q5_1 | f16 | 2.03 | 8,192 | fast |
| 4 | gemma-2-2b-it | 3 | IQ4_NL | q4_1 | f16 | 2.01 | 8,192 | fast |
| 5 | gemma-2-2b-it | 2 | IQ4_NL | q8_0 | q5_0 | 1.88 | 8,192 | fast |
| 6 | gemma-2-2b-it | 2 | IQ4_NL | q8_0 | q4_1 | 1.87 | 8,192 | fast |
| 7 | gemma-2-2b-it | 2 | IQ4_NL | q4_0 | q5_0 | 1.80 | 8,192 | fast |
| 8 | gemma-2-2b-it | 2 | IQ4_NL | q8_0 | f16 | 2.08 | 8,192 | fast |
| 9 | gemma-2-2b-it | 2 | IQ4_NL | q5_0 | q4_1 | 1.81 | 8,192 | fast |
| 10 | gemma-2-2b-it | 2 | IQ4_NL | q5_1 | iq4_nl | 1.81 | 8,192 | fast |
| 11 | gemma-2-2b-it | 2 | IQ4_NL | q5_1 | q4_0 | 1.81 | 8,192 | fast |
| 12 | gemma-2-2b-it | 2 | IQ4_NL | iq4_nl | q5_0 | 1.80 | 8,192 | fast |
| 13 | gemma-2-2b-it | 2 | IQ4_NL | q5_0 | q8_0 | 1.88 | 8,192 | fast |
| 14 | gemma-2-2b-it | 1 | IQ4_NL | iq4_nl | q8_0 | 1.86 | 8,192 | fast |
| 15 | gemma-2-2b-it | 1 | IQ4_NL | q4_1 | iq4_nl | 1.79 | 8,192 | fast |
| 16 | gemma-2-2b-it | 1 | IQ4_NL | q8_0 | q5_1 | 1.89 | 8,192 | fast |
| 17 | gemma-2-2b-it | 1 | IQ4_NL | q8_0 | iq4_nl | 1.86 | 8,192 | fast |
| 18 | gemma-2-2b-it | 1 | IQ4_NL | f16 | iq4_nl | 2.00 | 8,192 | fast |
| 19 | gemma-2-2b-it | 1 | IQ4_NL | f16 | q4_0 | 2.00 | 8,192 | fast |
| 20 | gemma-2-2b-it | 1 | IQ4_NL | iq4_nl | q5_1 | 1.81 | 8,192 | fast |
| 21 | gemma-2-2b-it | 1 | IQ4_NL | q5_1 | q5_1 | 1.84 | 8,192 | fast |
| 22 | gemma-2-2b-it | 1 | IQ4_NL | q4_0 | q4_1 | 1.79 | 8,192 | fast |
| 23 | gemma-2-2b-it | 1 | IQ4_NL | q4_1 | q8_0 | 1.87 | 8,192 | fast |
| 24 | gemma-2-2b-it | 1 | IQ4_NL | q5_0 | iq4_nl | 1.80 | 8,192 | fast |
| 25 | gemma-2-2b-it | 1 | IQ4_NL | f16 | q5_0 | 2.02 | 8,192 | fast |
| 26 | gemma-2-2b-it | 1 | IQ4_NL | iq4_nl | q4_0 | 1.78 | 8,192 | fast |
| 27 | gemma-2-2b-it | 1 | IQ4_NL | q4_1 | q5_1 | 1.82 | 8,192 | fast |
| 28 | gemma-2-2b-it | 1 | IQ4_NL | q8_0 | q4_0 | 1.86 | 8,192 | fast |
| 29 | gemma-2-2b-it | 0 | IQ4_NL | q4_0 | q5_1 | 1.81 | 8,192 | fast |
| 30 | gemma-2-2b-it | 0 | IQ4_NL | q4_1 | q5_0 | 1.81 | 8,192 | fast |
| 31 | gemma-2-2b-it | 0 | IQ4_NL | q4_0 | iq4_nl | 1.78 | 8,192 | fast |
| 32 | gemma-2-2b-it | 0 | IQ4_NL | q5_0 | q5_1 | 1.83 | 8,192 | fast |
| 33 | gemma-2-2b-it | 0 | IQ4_NL | iq4_nl | f16 | 2.00 | 8,192 | fast |
| 34 | gemma-2-2b-it | 0 | IQ4_NL | iq4_nl | q4_1 | 1.79 | 8,192 | fast |
| 35 | gemma-2-2b-it | 0 | IQ4_NL | q4_1 | q4_1 | 1.80 | 8,192 | fast |
| 36 | gemma-2-2b-it | 0 | IQ4_NL | f16 | f16 | 2.23 | 8,192 | fast |
| 37 | gemma-2-2b-it | 0 | IQ4_NL | q5_1 | q5_0 | 1.83 | 8,192 | fast |
| 38 | gemma-2-2b-it | 0 | IQ4_NL | q4_0 | f16 | 2.00 | 8,192 | fast |
| 39 | gemma-2-2b-it | 0 | IQ4_NL | q5_0 | q4_0 | 1.80 | 8,192 | fast |
| 40 | gemma-2-2b-it | 0 | IQ4_NL | f16 | q8_0 | 2.08 | 8,192 | fast |
| 41 | gemma-2-2b-it | 0 | IQ4_NL | iq4_nl | iq4_nl | 1.78 | 8,192 | fast |
| 42 | gemma-2-2b-it | 0 | IQ4_NL | q5_0 | f16 | 2.02 | 8,192 | fast |
| 43 | gemma-2-2b-it | 0 | IQ4_NL | q5_0 | q5_0 | 1.82 | 8,192 | fast |
| 44 | gemma-2-2b-it | 0 | IQ4_NL | q4_0 | q8_0 | 1.86 | 8,192 | fast |
| 45 | gemma-2-2b-it | 0 | IQ4_NL | q4_1 | q4_0 | 1.79 | 8,192 | fast |
| 46 | granite-4.0-h-350m | -1 | Q2_K_S | f16 | f16 | 5.18 | 1,048,576 | fast |
| 47 | granite-4.0-h-350m | -1 | Q2_K_S | f16 | q8_0 | 4.25 | 1,048,576 | fast |
| 48 | granite-4.0-h-350m | -1 | Q2_K_S | f16 | q4_0 | 3.75 | 1,048,576 | fast |
| 49 | granite-4.0-h-350m | -1 | Q2_K_S | f16 | q4_1 | 3.81 | 1,048,576 | fast |
| 50 | granite-4.0-h-350m | -1 | Q2_K_S | f16 | iq4_nl | 3.75 | 1,048,576 | fast |
| 51 | granite-4.0-h-350m | -1 | Q2_K_S | f16 | q5_0 | 3.87 | 1,048,576 | fast |
| 52 | granite-4.0-h-350m | -1 | Q2_K_S | f16 | q5_1 | 3.94 | 1,048,576 | fast |
| 53 | granite-4.0-h-350m | -1 | Q2_K_S | q8_0 | f16 | 4.25 | 1,048,576 | fast |
| 54 | granite-4.0-h-350m | -1 | Q2_K_S | q8_0 | q8_0 | 3.31 | 1,048,576 | fast |
| 55 | granite-4.0-h-350m | -1 | Q2_K_S | q8_0 | q4_0 | 2.81 | 1,048,576 | fast |
| 56 | granite-4.0-h-350m | -1 | Q2_K_S | q8_0 | q4_1 | 2.87 | 1,048,576 | fast |
| 57 | granite-4.0-h-350m | -1 | Q2_K_S | q8_0 | iq4_nl | 2.81 | 1,048,576 | fast |
| 58 | granite-4.0-h-350m | -1 | Q2_K_S | q8_0 | q5_0 | 2.94 | 1,048,576 | fast |
| 59 | granite-4.0-h-350m | -1 | Q2_K_S | q8_0 | q5_1 | 3.00 | 1,048,576 | fast |
| 60 | granite-4.0-h-350m | -1 | Q2_K_S | q4_0 | f16 | 3.75 | 1,048,576 | fast |
| 61 | granite-4.0-h-350m | -1 | Q2_K_S | q4_0 | q8_0 | 2.81 | 1,048,576 | fast |
| 62 | granite-4.0-h-350m | -1 | Q2_K_S | q4_0 | q4_0 | 2.31 | 1,048,576 | fast |
| 63 | granite-4.0-h-350m | -1 | Q2_K_S | q4_0 | q4_1 | 2.37 | 1,048,576 | fast |
| 64 | granite-4.0-h-350m | -1 | Q2_K_S | q4_0 | iq4_nl | 2.31 | 1,048,576 | fast |
| 65 | granite-4.0-h-350m | -1 | Q2_K_S | q4_0 | q5_0 | 2.44 | 1,048,576 | fast |
| 66 | granite-4.0-h-350m | -1 | Q2_K_S | q4_0 | q5_1 | 2.50 | 1,048,576 | fast |
| 67 | granite-4.0-h-350m | -1 | Q2_K_S | q4_1 | f16 | 3.81 | 1,048,576 | fast |
| 68 | granite-4.0-h-350m | -1 | Q2_K_S | q4_1 | q8_0 | 2.87 | 1,048,576 | fast |
| 69 | granite-4.0-h-350m | -1 | Q2_K_S | q4_1 | q4_0 | 2.37 | 1,048,576 | fast |
| 70 | granite-4.0-h-350m | -1 | Q2_K_S | q4_1 | q4_1 | 2.44 | 1,048,576 | fast |
| 71 | granite-4.0-h-350m | -1 | Q2_K_S | q4_1 | iq4_nl | 2.37 | 1,048,576 | fast |
| 72 | granite-4.0-h-350m | -1 | Q2_K_S | q4_1 | q5_0 | 2.50 | 1,048,576 | fast |
| 73 | granite-4.0-h-350m | -1 | Q2_K_S | q4_1 | q5_1 | 2.56 | 1,048,576 | fast |
| 74 | granite-4.0-h-350m | -1 | Q2_K_S | iq4_nl | f16 | 3.75 | 1,048,576 | fast |
| 75 | granite-4.0-h-350m | -1 | Q2_K_S | iq4_nl | q8_0 | 2.81 | 1,048,576 | fast |
| 76 | granite-4.0-h-350m | -1 | Q2_K_S | iq4_nl | q4_0 | 2.31 | 1,048,576 | fast |
| 77 | granite-4.0-h-350m | -1 | Q2_K_S | iq4_nl | q4_1 | 2.37 | 1,048,576 | fast |
| 78 | granite-4.0-h-350m | -1 | Q2_K_S | iq4_nl | iq4_nl | 2.31 | 1,048,576 | fast |
| 79 | granite-4.0-h-350m | -1 | Q2_K_S | iq4_nl | q5_0 | 2.44 | 1,048,576 | fast |
| 80 | granite-4.0-h-350m | -1 | Q2_K_S | iq4_nl | q5_1 | 2.50 | 1,048,576 | fast |
| 81 | granite-4.0-h-350m | -1 | Q2_K_S | q5_0 | f16 | 3.87 | 1,048,576 | fast |
| 82 | granite-4.0-h-350m | -1 | Q2_K_S | q5_0 | q8_0 | 2.94 | 1,048,576 | fast |
| 83 | granite-4.0-h-350m | -1 | Q2_K_S | q5_0 | q4_0 | 2.44 | 1,048,576 | fast |
| 84 | granite-4.0-h-350m | -1 | Q2_K_S | q5_0 | q4_1 | 2.50 | 1,048,576 | fast |
| 85 | granite-4.0-h-350m | -1 | Q2_K_S | q5_0 | iq4_nl | 2.44 | 1,048,576 | fast |
| 86 | granite-4.0-h-350m | -1 | Q2_K_S | q5_0 | q5_0 | 2.56 | 1,048,576 | fast |
| 87 | granite-4.0-h-350m | -1 | Q2_K_S | q5_0 | q5_1 | 2.62 | 1,048,576 | fast |
| 88 | granite-4.0-h-350m | -1 | Q2_K_S | q5_1 | f16 | 3.94 | 1,048,576 | fast |
| 89 | granite-4.0-h-350m | -1 | Q2_K_S | q5_1 | q8_0 | 3.00 | 1,048,576 | fast |
| 90 | granite-4.0-h-350m | -1 | Q2_K_S | q5_1 | q4_0 | 2.50 | 1,048,576 | fast |
| 91 | granite-4.0-h-350m | -1 | Q2_K_S | q5_1 | q4_1 | 2.56 | 1,048,576 | fast |
| 92 | granite-4.0-h-350m | -1 | Q2_K_S | q5_1 | iq4_nl | 2.50 | 1,048,576 | fast |
| 93 | granite-4.0-h-350m | -1 | Q2_K_S | q5_1 | q5_0 | 2.62 | 1,048,576 | fast |
| 94 | granite-4.0-h-350m | -1 | Q2_K_S | q5_1 | q5_1 | 2.69 | 1,048,576 | fast |
| 95 | MiniCPM5-1B | -1 | Q3_K_L | f16 | f16 | 3.65 | 131,072 | slow |
| 96 | MiniCPM5-1B | -1 | Q3_K_L | f16 | q8_0 | 2.94 | 131,072 | slow |
| 97 | MiniCPM5-1B | -1 | Q3_K_L | f16 | q4_0 | 2.56 | 131,072 | slow |
| 98 | MiniCPM5-1B | -1 | Q3_K_L | f16 | q4_1 | 2.61 | 131,072 | slow |
| 99 | MiniCPM5-1B | -1 | Q3_K_L | f16 | iq4_nl | 2.56 | 131,072 | slow |
| 100 | MiniCPM5-1B | -1 | Q3_K_L | f16 | q5_0 | 2.66 | 131,072 | slow |
| 101 | MiniCPM5-1B | -1 | Q3_K_L | f16 | q5_1 | 2.71 | 131,072 | slow |
| 102 | MiniCPM5-1B | -1 | Q3_K_L | q8_0 | f16 | 2.94 | 131,072 | slow |
| 103 | MiniCPM5-1B | -1 | Q3_K_L | q8_0 | q8_0 | 2.24 | 131,072 | slow |
| 104 | MiniCPM5-1B | -1 | Q3_K_L | q8_0 | q4_0 | 1.87 | 131,072 | slow |
| 105 | MiniCPM5-1B | -1 | Q3_K_L | q8_0 | q4_1 | 1.92 | 131,072 | slow |
| 106 | MiniCPM5-1B | -1 | Q3_K_L | q8_0 | iq4_nl | 1.87 | 131,072 | slow |
| 107 | MiniCPM5-1B | -1 | Q3_K_L | q8_0 | q5_0 | 1.96 | 131,072 | slow |
| 108 | MiniCPM5-1B | -1 | Q3_K_L | q8_0 | q5_1 | 2.01 | 131,072 | slow |
| 109 | MiniCPM5-1B | -1 | Q3_K_L | q4_0 | f16 | 2.56 | 131,072 | slow |
| 110 | MiniCPM5-1B | -1 | Q3_K_L | q4_0 | q8_0 | 1.87 | 131,072 | slow |
| 111 | MiniCPM5-1B | -1 | Q3_K_L | q4_0 | q4_0 | 1.49 | 131,072 | slow |
| 112 | MiniCPM5-1B | -1 | Q3_K_L | q4_0 | q4_1 | 1.54 | 131,072 | slow |
| 113 | MiniCPM5-1B | -1 | Q3_K_L | q4_0 | iq4_nl | 1.49 | 131,072 | slow |
| 114 | MiniCPM5-1B | -1 | Q3_K_L | q4_0 | q5_0 | 1.59 | 131,072 | slow |
| 115 | MiniCPM5-1B | -1 | Q3_K_L | q4_0 | q5_1 | 1.63 | 131,072 | slow |
| 116 | MiniCPM5-1B | -1 | Q3_K_L | q4_1 | f16 | 2.61 | 131,072 | slow |
| 117 | MiniCPM5-1B | -1 | Q3_K_L | q4_1 | q8_0 | 1.92 | 131,072 | slow |
| 118 | MiniCPM5-1B | -1 | Q3_K_L | q4_1 | q4_0 | 1.54 | 131,072 | slow |
| 119 | MiniCPM5-1B | -1 | Q3_K_L | q4_1 | q4_1 | 1.59 | 131,072 | slow |
| 120 | MiniCPM5-1B | -1 | Q3_K_L | q4_1 | iq4_nl | 1.54 | 131,072 | slow |
| 121 | MiniCPM5-1B | -1 | Q3_K_L | q4_1 | q5_0 | 1.63 | 131,072 | slow |
| 122 | MiniCPM5-1B | -1 | Q3_K_L | q4_1 | q5_1 | 1.68 | 131,072 | slow |
| 123 | MiniCPM5-1B | -1 | Q3_K_L | iq4_nl | f16 | 2.56 | 131,072 | slow |
| 124 | MiniCPM5-1B | -1 | Q3_K_L | iq4_nl | q8_0 | 1.87 | 131,072 | slow |
| 125 | MiniCPM5-1B | -1 | Q3_K_L | iq4_nl | q4_0 | 1.49 | 131,072 | slow |
| 126 | MiniCPM5-1B | -1 | Q3_K_L | iq4_nl | q4_1 | 1.54 | 131,072 | slow |
| 127 | MiniCPM5-1B | -1 | Q3_K_L | iq4_nl | iq4_nl | 1.49 | 131,072 | slow |
| 128 | MiniCPM5-1B | -1 | Q3_K_L | iq4_nl | q5_0 | 1.59 | 131,072 | slow |
| 129 | MiniCPM5-1B | -1 | Q3_K_L | iq4_nl | q5_1 | 1.63 | 131,072 | slow |
| 130 | MiniCPM5-1B | -1 | Q3_K_L | q5_0 | f16 | 2.66 | 131,072 | slow |
| 131 | MiniCPM5-1B | -1 | Q3_K_L | q5_0 | q8_0 | 1.96 | 131,072 | slow |
| 132 | MiniCPM5-1B | -1 | Q3_K_L | q5_0 | q4_0 | 1.59 | 131,072 | slow |
| 133 | MiniCPM5-1B | -1 | Q3_K_L | q5_0 | q4_1 | 1.63 | 131,072 | slow |
| 134 | MiniCPM5-1B | -1 | Q3_K_L | q5_0 | iq4_nl | 1.59 | 131,072 | slow |
| 135 | MiniCPM5-1B | -1 | Q3_K_L | q5_0 | q5_0 | 1.68 | 131,072 | slow |
| 136 | MiniCPM5-1B | -1 | Q3_K_L | q5_0 | q5_1 | 1.73 | 131,072 | slow |
| 137 | MiniCPM5-1B | -1 | Q3_K_L | q5_1 | f16 | 2.71 | 131,072 | slow |
| 138 | MiniCPM5-1B | -1 | Q3_K_L | q5_1 | q8_0 | 2.01 | 131,072 | slow |
| 139 | MiniCPM5-1B | -1 | Q3_K_L | q5_1 | q4_0 | 1.63 | 131,072 | slow |
| 140 | MiniCPM5-1B | -1 | Q3_K_L | q5_1 | q4_1 | 1.68 | 131,072 | slow |
| 141 | MiniCPM5-1B | -1 | Q3_K_L | q5_1 | iq4_nl | 1.63 | 131,072 | slow |
| 142 | MiniCPM5-1B | -1 | Q3_K_L | q5_1 | q5_0 | 1.73 | 131,072 | slow |
| 143 | MiniCPM5-1B | -1 | Q3_K_L | q5_1 | q5_1 | 1.77 | 131,072 | slow |
| 144 | granite-3.1-2b-instruct | -1 | IQ1_S | f16 | f16 | 10.73 | 131,072 | slow |
| 145 | granite-3.1-2b-instruct | -1 | IQ1_S | f16 | q8_0 | 8.39 | 131,072 | slow |
| 146 | granite-3.1-2b-instruct | -1 | IQ1_S | f16 | q4_0 | 7.14 | 131,072 | slow |
| 147 | granite-3.1-2b-instruct | -1 | IQ1_S | f16 | q4_1 | 7.29 | 131,072 | slow |
| 148 | granite-3.1-2b-instruct | -1 | IQ1_S | f16 | iq4_nl | 7.14 | 131,072 | slow |
| 149 | granite-3.1-2b-instruct | -1 | IQ1_S | f16 | q5_0 | 7.45 | 131,072 | slow |
| 150 | granite-3.1-2b-instruct | -1 | IQ1_S | f16 | q5_1 | 7.61 | 131,072 | slow |
| 151 | granite-3.1-2b-instruct | -1 | IQ1_S | q8_0 | f16 | 8.39 | 131,072 | slow |
| 152 | granite-3.1-2b-instruct | -1 | IQ1_S | q8_0 | q8_0 | 6.04 | 131,072 | slow |
| 153 | granite-3.1-2b-instruct | -1 | IQ1_S | q8_0 | q4_0 | 4.79 | 131,072 | slow |
| 154 | granite-3.1-2b-instruct | -1 | IQ1_S | q8_0 | q4_1 | 4.95 | 131,072 | slow |
| 155 | granite-3.1-2b-instruct | -1 | IQ1_S | q8_0 | iq4_nl | 4.79 | 131,072 | slow |
| 156 | granite-3.1-2b-instruct | -1 | IQ1_S | q8_0 | q5_0 | 5.11 | 131,072 | slow |
| 157 | granite-3.1-2b-instruct | -1 | IQ1_S | q8_0 | q5_1 | 5.26 | 131,072 | slow |
| 158 | granite-3.1-2b-instruct | -1 | IQ1_S | q4_0 | f16 | 7.14 | 131,072 | slow |
| 159 | granite-3.1-2b-instruct | -1 | IQ1_S | q4_0 | q8_0 | 4.79 | 131,072 | slow |
| 160 | granite-3.1-2b-instruct | -1 | IQ1_S | q4_0 | q4_0 | 3.54 | 131,072 | slow |
| 161 | granite-3.1-2b-instruct | -1 | IQ1_S | q4_0 | q4_1 | 3.70 | 131,072 | slow |
| 162 | granite-3.1-2b-instruct | -1 | IQ1_S | q4_0 | iq4_nl | 3.54 | 131,072 | slow |
| 163 | granite-3.1-2b-instruct | -1 | IQ1_S | q4_0 | q5_0 | 3.85 | 131,072 | slow |
| 164 | granite-3.1-2b-instruct | -1 | IQ1_S | q4_0 | q5_1 | 4.01 | 131,072 | slow |
| 165 | granite-3.1-2b-instruct | -1 | IQ1_S | q4_1 | f16 | 7.29 | 131,072 | slow |
| 166 | granite-3.1-2b-instruct | -1 | IQ1_S | q4_1 | q8_0 | 4.95 | 131,072 | slow |
| 167 | granite-3.1-2b-instruct | -1 | IQ1_S | q4_1 | q4_0 | 3.70 | 131,072 | slow |
| 168 | granite-3.1-2b-instruct | -1 | IQ1_S | q4_1 | q4_1 | 3.85 | 131,072 | slow |
| 169 | granite-3.1-2b-instruct | -1 | IQ1_S | q4_1 | iq4_nl | 3.70 | 131,072 | slow |
| 170 | granite-3.1-2b-instruct | -1 | IQ1_S | q4_1 | q5_0 | 4.01 | 131,072 | slow |
| 171 | granite-3.1-2b-instruct | -1 | IQ1_S | q4_1 | q5_1 | 4.17 | 131,072 | slow |
| 172 | granite-3.1-2b-instruct | -1 | IQ1_S | iq4_nl | f16 | 7.14 | 131,072 | slow |
| 173 | granite-3.1-2b-instruct | -1 | IQ1_S | iq4_nl | q8_0 | 4.79 | 131,072 | slow |
| 174 | granite-3.1-2b-instruct | -1 | IQ1_S | iq4_nl | q4_0 | 3.54 | 131,072 | slow |
| 175 | granite-3.1-2b-instruct | -1 | IQ1_S | iq4_nl | q4_1 | 3.70 | 131,072 | slow |
| 176 | granite-3.1-2b-instruct | -1 | IQ1_S | iq4_nl | iq4_nl | 3.54 | 131,072 | slow |
| 177 | granite-3.1-2b-instruct | -1 | IQ1_S | iq4_nl | q5_0 | 3.85 | 131,072 | slow |
| 178 | granite-3.1-2b-instruct | -1 | IQ1_S | iq4_nl | q5_1 | 4.01 | 131,072 | slow |
| 179 | granite-3.1-2b-instruct | -1 | IQ1_S | q5_0 | f16 | 7.45 | 131,072 | slow |
| 180 | granite-3.1-2b-instruct | -1 | IQ1_S | q5_0 | q8_0 | 5.11 | 131,072 | slow |
| 181 | granite-3.1-2b-instruct | -1 | IQ1_S | q5_0 | q4_0 | 3.85 | 131,072 | slow |
| 182 | granite-3.1-2b-instruct | -1 | IQ1_S | q5_0 | q4_1 | 4.01 | 131,072 | slow |
| 183 | granite-3.1-2b-instruct | -1 | IQ1_S | q5_0 | iq4_nl | 3.85 | 131,072 | slow |
| 184 | granite-3.1-2b-instruct | -1 | IQ1_S | q5_0 | q5_0 | 4.17 | 131,072 | slow |
| 185 | granite-3.1-2b-instruct | -1 | IQ1_S | q5_0 | q5_1 | 4.32 | 131,072 | slow |
| 186 | granite-3.1-2b-instruct | -1 | IQ1_S | q5_1 | f16 | 7.61 | 131,072 | slow |
| 187 | granite-3.1-2b-instruct | -1 | IQ1_S | q5_1 | q8_0 | 5.26 | 131,072 | slow |
| 188 | granite-3.1-2b-instruct | -1 | IQ1_S | q5_1 | q4_0 | 4.01 | 131,072 | slow |
| 189 | granite-3.1-2b-instruct | -1 | IQ1_S | q5_1 | q4_1 | 4.17 | 131,072 | slow |
| 190 | granite-3.1-2b-instruct | -1 | IQ1_S | q5_1 | iq4_nl | 4.01 | 131,072 | slow |
| 191 | granite-3.1-2b-instruct | -1 | IQ1_S | q5_1 | q5_0 | 4.32 | 131,072 | slow |
| 192 | granite-3.1-2b-instruct | -1 | IQ1_S | q5_1 | q5_1 | 4.48 | 131,072 | slow |
| 193 | gemma-2-2b-it | -1 | IQ4_NL | f16 | q4_1 | 2.01 | 8,192 | fast |
| 194 | gemma-2-2b-it | -1 | IQ4_NL | q8_0 | q8_0 | 1.94 | 8,192 | slow |
| 195 | gemma-2-2b-it | -1 | IQ4_NL | q4_0 | q4_0 | 1.78 | 8,192 | fast |
| 196 | gemma-2-2b-it | -1 | IQ4_NL | q5_1 | q8_0 | 1.89 | 8,192 | fast |

_196 candidates run of 100,352 (5 of 2,048 pairs swept); each pair one acquisition, the seed recorded in state._
