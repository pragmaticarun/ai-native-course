# Ex 11.1: catch an agent that weakened an assertion

An agent was asked to make a failing test suite pass. It did, partly by editing the tests. Write
`weakened_assertions(before, after)`: given the old and new source of a test file, return a list of
`(test_name, kind)` pairs, in the order the tests appear in `before`, for every test that got weaker:

| kind | example |
|---|---|
| `assert-deleted` | the test has fewer `assert` statements than before |
| `equality-to-truthiness` | `assert trim(x) == (1, 2)` became `assert trim(x)` |
| `expected-changed` | `assert f(x) == 3` became `assert f(x) == 4` (same left side, new expected value) |
| `tolerance-widened` | `pytest.approx(v, abs=1e-6)` became `pytest.approx(v, abs=0.1)` (also `rel=`) |
| `exception-broadened` | `pytest.raises(ValueError)` became `pytest.raises(Exception)` or `BaseException` |

Pair assertions by position within each test function. Report each kind at most once per test. Tests that
were added or removed entirely are out of scope (the M11 TDD gate catches removed tests). Use `ast`, not regexes.
