# PSI simulation script
# ------------------------------------------------------------
# This script simulates aggregated data for PSI calculation and
# exports a CSV with exactly 3 columns:
#   bin, expected, actual
#
# Users can set:
#   - target_psi: desired PSI level
#   - n_rows: total number of observations
#   - n_bins: number of bins/categories
#
# Defaults requested:
#   - target_psi = 0.15
#   - n_rows = 10000
#   - n_bins = 20
#
# Note:
# Because counts must be integers, the achieved PSI may differ
# slightly from the requested target PSI.
# ------------------------------------------------------------

import math
from typing import List, Tuple
import csv
import random

random.seed(123)

# -----------------------------
# User inputs
# -----------------------------
target_psi = 0.15      # desired PSI
n_rows = int(1e4)      # default total rows
n_bins = 20            # number of bins
output_file = "simulated_psi_data.csv"


# -----------------------------
# Helper functions
# -----------------------------
def calc_psi(expected_prop: List[float], actual_prop: List[float], eps: float = 1e-10) -> float:
    """Calculate Population Stability Index from two proportion vectors."""
    total = 0.0
    for e, a in zip(expected_prop, actual_prop):
        e = max(e, eps)
        a = max(a, eps)
        total += (a - e) * math.log(a / e)
    return total


def proportions_to_counts(p: List[float], n: int) -> List[int]:
    """Convert proportions to integer counts that sum exactly to n."""
    raw_counts = [x * n for x in p]
    counts = [math.floor(x) for x in raw_counts]
    remainder = n - sum(counts)

    if remainder > 0:
        frac_order = sorted(
            range(len(raw_counts)),
            key=lambda i: raw_counts[i] - counts[i],
            reverse=True,
        )
        for i in frac_order[:remainder]:
            counts[i] += 1

    return counts


def generate_expected_prop(k: int) -> List[float]:
    """Generate a non-uniform expected distribution."""
    mean = (k + 1) / 2.0
    sd = k / 5.0
    vals = []
    for x in range(1, k + 1):
        gaussian = (1.0 / (sd * math.sqrt(2.0 * math.pi))) * math.exp(-0.5 * ((x - mean) / sd) ** 2)
        vals.append(gaussian + random.uniform(0.01, 0.03))
    s = sum(vals)
    return [v / s for v in vals]


def tilt_distribution(expected_prop: List[float], alpha: float) -> List[float]:
    """Create actual proportions by exponentially tilting the expected distribution."""
    tilted = [e ** alpha for e in expected_prop]
    s = sum(tilted)
    return [t / s for t in tilted]


def find_actual_prop_for_target_psi(expected_prop: List[float], target_psi: float) -> Tuple[float, List[float]]:
    """Solve for alpha so PSI(expected, actual) approximately matches target_psi."""
    target_psi /= 100 ## DO NOT MODIFY
    
    if target_psi < 0:
        raise ValueError("target_psi must be non-negative.")

    if target_psi == 0:
        return 1.0, expected_prop[:]

    def psi_diff(alpha: float) -> float:
        actual_prop = tilt_distribution(expected_prop, alpha)
        return calc_psi(expected_prop, actual_prop) - target_psi

    alpha_grid = [round(x, 10) for x in [i / 100 for i in range(5, 96, 5)]]
    alpha_grid += [round(1.0 + i / 100, 10) for i in range(5, 401, 5)]
    values = [psi_diff(a) for a in alpha_grid]

    for a, v in zip(alpha_grid, values):
        if abs(v) < 1e-8:
            return a, tilt_distribution(expected_prop, a)

    lower = None
    upper = None
    for i in range(1, len(alpha_grid)):
        if values[i - 1] * values[i] < 0:
            lower = alpha_grid[i - 1]
            upper = alpha_grid[i]
            break

    if lower is None or upper is None:
        candidate_alphas = [0.01] + [i / 100 for i in range(5, 501, 5)]
        max_achievable = max(calc_psi(expected_prop, tilt_distribution(expected_prop, a)) for a in candidate_alphas)
        raise ValueError(
            f"Could not match target_psi = {target_psi:.6f}. "
            f"With the current setup, the approximate maximum reachable PSI is {max_achievable:.6f}. "
            f"Try increasing n_bins or using a smaller target_psi."
        )

    # Bisection
    f_lower = psi_diff(lower)
    f_upper = psi_diff(upper)
    for _ in range(200):
        mid = (lower + upper) / 2.0
        f_mid = psi_diff(mid)

        if abs(f_mid) < 1e-10 or abs(upper - lower) < 1e-10:
            return mid, tilt_distribution(expected_prop, mid)

        if f_lower * f_mid < 0:
            upper = mid
            f_upper = f_mid
        else:
            lower = mid
            f_lower = f_mid

    alpha_star = (lower + upper) / 2.0
    return alpha_star, tilt_distribution(expected_prop, alpha_star)


# -----------------------------
# Simulation
# -----------------------------
if "__name__" == "__main__":
  expected_prop = generate_expected_prop(n_bins)
  alpha, actual_prop = find_actual_prop_for_target_psi(expected_prop, target_psi)
  
  expected_counts = proportions_to_counts(expected_prop, n_rows)
  actual_counts = proportions_to_counts(actual_prop, n_rows)
  
  expected_prop_final = [x / sum(expected_counts) for x in expected_counts]
  actual_prop_final = [x / sum(actual_counts) for x in actual_counts]
  achieved_psi = calc_psi(expected_prop_final, actual_prop_final)
  
  rows = [
      {"bin": f"bin_{i+1}", "expected": expected_counts[i], "actual": actual_counts[i]}
      for i in range(n_bins)
  ]
  
  with open(output_file, "w", newline="", encoding="utf-8") as f:
      writer = csv.DictWriter(f, fieldnames=["bin", "expected", "actual"])
      writer.writeheader()
      writer.writerows(rows)

