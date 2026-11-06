"""FSRS-4.5 memory model: pure functions, no I/O.

Each card carries two numbers: stability S (days for retrievability to fall
from 100% to 90%) and difficulty D (1 easy .. 10 hard). Retrievability R is
derived from S and the days elapsed since the last review. The next interval
is the number of days until R falls to the target retention.

Default parameters are the published FSRS-4.5 weights. The review_events log
holds the data to fit per-user weights later.
"""

import math

DEFAULT_W = (
    0.4872, 1.4003, 3.7145, 13.8206, 5.1618, 1.2298, 0.8975, 0.031,
    1.6474, 0.1367, 1.0461, 2.1072, 0.0793, 0.3246, 1.587, 0.2272, 2.8755,
)
DECAY = -0.5
FACTOR = 19.0 / 81.0  # chosen so that R(S, S) == 0.9
DESIRED_RETENTION = 0.9
MIN_STABILITY = 0.01
MAX_INTERVAL_DAYS = 36500

AGAIN, HARD, GOOD, EASY = 1, 2, 3, 4


def clamp_difficulty(d: float) -> float:
    return min(10.0, max(1.0, d))


def retrievability(elapsed_days: float, stability: float) -> float:
    return (1 + FACTOR * max(0.0, elapsed_days) / stability) ** DECAY


def next_interval(
    stability: float, retention: float = DESIRED_RETENTION
) -> int:
    days = stability / FACTOR * (retention ** (1 / DECAY) - 1)
    return int(min(MAX_INTERVAL_DAYS, max(1, round(days))))


def initial_stability(rating: int, w=DEFAULT_W) -> float:
    return max(MIN_STABILITY, w[rating - 1])


def initial_difficulty(rating: int, w=DEFAULT_W) -> float:
    return clamp_difficulty(w[4] - (rating - 3) * w[5])


def next_difficulty(d: float, rating: int, w=DEFAULT_W) -> float:
    shifted = d - w[6] * (rating - 3)
    # Mean reversion toward the difficulty of an "Easy" first review.
    reverted = w[7] * initial_difficulty(EASY, w) + (1 - w[7]) * shifted
    return clamp_difficulty(reverted)


def next_stability(
    d: float, s: float, r: float, rating: int, w=DEFAULT_W
) -> float:
    if rating == AGAIN:
        new = (
            w[11]
            * d ** -w[12]
            * ((s + 1) ** w[13] - 1)
            * math.exp(w[14] * (1 - r))
        )
        return max(MIN_STABILITY, min(new, s))
    hard_penalty = w[15] if rating == HARD else 1.0
    easy_bonus = w[16] if rating == EASY else 1.0
    growth = (
        math.exp(w[8])
        * (11 - d)
        * s ** -w[9]
        * (math.exp(w[10] * (1 - r)) - 1)
        * hard_penalty
        * easy_bonus
    )
    return max(s, s * (1 + growth))


def review(
    stability: float | None,
    difficulty: float | None,
    elapsed_days: float,
    rating: int,
    w=DEFAULT_W,
) -> tuple[float, float]:
    """Return (stability, difficulty) after one review. A None stability is
    a card that has never been reviewed."""
    if stability is None or difficulty is None:
        return initial_stability(rating, w), initial_difficulty(rating, w)
    r = retrievability(elapsed_days, stability)
    return (
        next_stability(difficulty, stability, r, rating, w),
        next_difficulty(difficulty, rating, w),
    )


# Legacy SM-2 ease factor <-> FSRS difficulty. Ease 2.5 (the SM-2 default)
# maps to D=5 (about where FSRS starts a Good first review); ease 1.3 (the
# floor) maps to 9; high ease maps toward 1. Linear, so it round-trips.
_EASE_DEFAULT = 2.5
_EASE_MIN = 1.3
_D_AT_DEFAULT = 5.0
_D_PER_EASE = 4.0 / 1.2


def difficulty_from_ease(ease: float) -> float:
    return clamp_difficulty(_D_AT_DEFAULT - (ease - _EASE_DEFAULT) * _D_PER_EASE)


def ease_from_difficulty(d: float) -> float:
    return max(_EASE_MIN, _EASE_DEFAULT - (d - _D_AT_DEFAULT) / _D_PER_EASE)
