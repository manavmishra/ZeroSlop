Local tools score the draft first. Then the meter reports what moved, and the
scorer keeps a frozen copy for the regression suite. When the numbers disagree,
our own checks win, because the local checker is the only part that never
changes between runs. The pipeline hands the rest to review.
