"""Pins: R-25 (session 44, addendum 120). K=2: the 10x-easier cell.

The author's ruling: "The rest is too hard. It takes forever to run
a cell. Make it 10 times easier." The lever is K (questions per
(span, hops) grade): 20 -> 2 cuts the worst-case cell from 800
questions to 80 - exactly 10x - while the grade grid (spans x hops)
and the all-h+1-names pass rule stay untouched.
"""

import bench.v7 as v7


def test_k_is_two():
    assert v7.K == 2, "addendum 120: K=2 keeps a cell at ~80 questions (10x easier)"


def test_cell_question_count_is_ten_times_smaller():
    worst = len(v7.SPANS) * len(v7.HOPS) * v7.K
    assert worst == 80, "8 spans x 5 hops x K=2 = 80 questions per full cell"
