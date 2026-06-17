"""Generic 1-D optimisation helpers used by the design studio.

Pure-numeric building blocks (no simulation knowledge) so they are easy to test
and reuse: golden-section optimisation of a unimodal objective, and a robust
root-find that drives a (mostly monotonic) function to a target value by
bracketing a sign change and bisecting, falling back to the sampled best.
"""

from __future__ import annotations

import math
from collections.abc import Callable

_GR = (math.sqrt(5.0) - 1.0) / 2.0


def golden_section_minimize(
    f: Callable[[float], float], a: float, b: float, iters: int = 40
) -> float:
    """Return x in [a, b] minimising a unimodal ``f``."""
    c = b - _GR * (b - a)
    d = a + _GR * (b - a)
    fc, fd = f(c), f(d)
    for _ in range(iters):
        if fc < fd:
            b, d, fd = d, c, fc
            c = b - _GR * (b - a)
            fc = f(c)
        else:
            a, c, fc = c, d, fd
            d = a + _GR * (b - a)
            fd = f(d)
    return 0.5 * (a + b)


def golden_section_maximize(
    f: Callable[[float], float], a: float, b: float, iters: int = 40
) -> float:
    """Return x in [a, b] maximising a unimodal ``f``."""
    return golden_section_minimize(lambda x: -f(x), a, b, iters)


def solve_to_target(
    f: Callable[[float], float],
    target: float,
    a: float,
    b: float,
    *,
    samples: int = 24,
    iters: int = 40,
) -> float:
    """Find x in [a, b] with ``f(x) ≈ target``.

    Samples the interval to bracket a sign change of ``g = f - target`` and
    bisects it; if ``g`` never changes sign (target out of reach or non-
    monotonic), returns the sampled x minimising ``|g|``.
    """
    def g(x: float) -> float:
        return f(x) - target

    xs = [a + (b - a) * i / (samples - 1) for i in range(samples)]
    gs = [g(x) for x in xs]

    best_x, best_abs = xs[0], abs(gs[0])
    for x, gv in zip(xs[1:], gs[1:], strict=False):
        if abs(gv) < best_abs:
            best_abs, best_x = abs(gv), x

    bracket = None
    for i in range(len(xs) - 1):
        if gs[i] == 0.0:
            return xs[i]
        if gs[i] * gs[i + 1] < 0.0:
            bracket = (xs[i], xs[i + 1], gs[i])
            break
    if bracket is None:
        return best_x

    lo, hi, g_lo = bracket
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        g_mid = g(mid)
        if g_mid == 0.0:
            return mid
        if g_lo * g_mid < 0.0:
            hi = mid
        else:
            lo, g_lo = mid, g_mid
    return 0.5 * (lo + hi)
