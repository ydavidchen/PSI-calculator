# PSI simulation script
# ------------------------------------------------------------
# This script simulates aggregated data for PSI calculation and
# exports a CSV with exactly 3 columns:
#   bin, expected, actual
#
# Users can set:
#   - target_psi: desired PSI level
#   - n_rows: total number of observations (default = 100)
#   - n_bins: number of bins/categories
#
# Note:
# Because counts must be integers, the achieved PSI may differ
# slightly from the requested target PSI.
# ------------------------------------------------------------

# -----------------------------
# User inputs
# -----------------------------
target_psi <- 0.2
n_bins <- 20
SEED <- 42
n_rows <- 1e4       
output_file <- "simulated_data_psi.csv"

# -----------------------------
# Helper functions
# -----------------------------
# PSI formula using proportions
calc_psi <- function(expected_prop, actual_prop, eps=1e-10) {
  expected_prop <- pmax(expected_prop, eps)
  actual_prop   <- pmax(actual_prop, eps)
  sum((actual_prop - expected_prop) * log(actual_prop / expected_prop))
}

# Convert proportions to integer counts that sum exactly to n
proportions_to_counts <- function(p, n) {
  raw_counts <- p * n
  counts <- floor(raw_counts)
  remainder <- n - sum(counts)

  if (remainder > 0) {
    add_idx <- order(raw_counts - counts, decreasing = TRUE)[1:remainder]
    counts[add_idx] <- counts[add_idx] + 1
  }

  counts
}

# Generate a non-uniform expected distribution
generate_expected_prop <- function(k) {
  x <- seq(1, k)
  base <- dnorm(x, mean = (k + 1) / 2, sd = k / 5) + runif(k, 0.01, 0.03)
  base / sum(base)
}

# Create actual proportions by exponentially tilting the expected distribution
# a_i(alpha) ∝ e_i ^ alpha
tilt_distribution <- function(expected_prop, alpha) {
  tilted <- expected_prop ^ alpha
  tilted / sum(tilted)
}

# Solve for alpha so that PSI(expected, actual) matches target_psi
find_actual_prop_for_target_psi <- function(expected_prop, target_psi) {
  target_psi <- target_psi / 100 ### DO NOT EDIT!
  
  if (target_psi < 0) {
    stop("target_psi must be non-negative.")
  }

  # PSI = 0 when actual = expected
  if (target_psi == 0) {
    return(list(alpha = 1, actual_prop = expected_prop))
  }

  psi_fn <- function(alpha) {
    actual_prop <- tilt_distribution(expected_prop, alpha)
    calc_psi(expected_prop, actual_prop) - target_psi
  }

  # Search for a bracket where the function changes sign
  # Start from alpha near 1 and expand outward.
  alpha_grid <- c(seq(0.05, 0.95, by = 0.05), seq(1.05, 5, by = 0.05))
  values <- sapply(alpha_grid, psi_fn)

  hit_idx <- which(abs(values) < 1e-8)
  if (length(hit_idx) > 0) {
    alpha_star <- alpha_grid[hit_idx[1]]
    return(list(alpha = alpha_star,
                actual_prop = tilt_distribution(expected_prop, alpha_star)))
  }

  bracket_found <- FALSE
  lower <- NA
  upper <- NA

  for (i in 2:length(alpha_grid)) {
    if (values[i - 1] * values[i] < 0) {
      lower <- alpha_grid[i - 1]
      upper <- alpha_grid[i]
      bracket_found <- TRUE
      break
    }
  }

  if (!bracket_found) {
    max_achievable <- max(sapply(c(0.01, seq(0.05, 5, by = 0.05)), function(a) {
      calc_psi(expected_prop, tilt_distribution(expected_prop, a))
    }))

    stop(
      paste0(
        "Could not match target_psi = ", round(target_psi, 6),
        ". With the current setup, the approximate maximum reachable PSI is ",
        round(max_achievable, 6),
        ". Try increasing n_bins or using a smaller target_psi."
      )
    )
  }

  root <- uniroot(psi_fn, interval = c(lower, upper), tol = 1e-10)
  alpha_star <- root$root

  list(alpha = alpha_star,
       actual_prop = tilt_distribution(expected_prop, alpha_star))
}

# -----------------------------
# Main: Simulation
# -----------------------------
main <- function() {
  set.seed(SEED)
  
  expected_prop <- generate_expected_prop(n_bins)
  
  solution <- find_actual_prop_for_target_psi(expected_prop, target_psi)
  actual_prop <- solution$actual_prop
  
  expected_counts <- proportions_to_counts(expected_prop, n_rows)
  actual_counts   <- proportions_to_counts(actual_prop, n_rows)
  
  # Recalculate achieved PSI using integer counts
  expected_prop_final <- expected_counts / sum(expected_counts)
  actual_prop_final   <- actual_counts / sum(actual_counts)
  achieved_psi <- calc_psi(expected_prop_final, actual_prop_final)
  
  simulated_data <- data.frame(
    bin = paste0("bin_", seq_len(n_bins)),
    expected = expected_counts,
    actual = actual_counts
  )
  
  write.csv(simulated_data, output_file, row.names = FALSE)
}

if(! interactive()) main()
