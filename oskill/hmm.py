"""Hidden Markov Model workflows."""

from __future__ import annotations

import numpy as np


def gaussian_hmm(
    x: np.ndarray,
    n_states: int = 2,
    n_iter: int = 100,
    tol: float = 1e-4,
    random_state: int | None = None,
) -> dict:
    """Fit Gaussian HMM via Baum-Welch EM algorithm.

    Supports both univariate (1-D) and multivariate (2-D) observations.

    Parameters
    ----------
    x : np.ndarray
        Observation sequence. Shape (T,) for univariate or (T, D) for multivariate.
    n_states : int
        Number of hidden states.
    n_iter : int
        Maximum EM iterations.
    tol : float
        Convergence tolerance on log-likelihood.
    random_state : int, optional
        RNG seed.

    Returns
    -------
    dict
        "means": state means — shape (K,) univariate or (K, D) multivariate,
        "stds": state stds (univariate only),
        "covariances": state covariance diagonals (multivariate only) — shape (K, D),
        "transition_matrix": (K, K),
        "state_probs": posterior state probabilities (T, K),
        "viterbi_path": most likely state sequence (T,),
        "log_likelihood": final log-likelihood,
        "converged": bool.

    References
    ----------
    .. [1] Baum, L.E. et al. (1970). A maximization technique in statistical
           analysis of probabilistic functions of Markov chains.
    .. [2] Extraction source: Selene project, sel_v2/observation_tools/bayesian_hmm.py
    .. [3] Multivariate extension for Helixa regime-detector (diagonal covariance).
    """
    rng = np.random.default_rng(random_state)
    x = np.asarray(x, dtype=float)

    if x.ndim == 1:
        return _fit_univariate(x, n_states, n_iter, tol, rng)
    elif x.ndim == 2:
        return _fit_multivariate(x, n_states, n_iter, tol, rng)
    else:
        raise ValueError(f"x must be 1-D or 2-D, got ndim={x.ndim}")


# ======================================================================
# Univariate implementation (original)
# ======================================================================


def _fit_univariate(x, n_states, n_iter, tol, rng):
    T = len(x)
    K = n_states

    means = np.linspace(x.min(), x.max(), K)
    stds = np.full(K, x.std() / K)
    A = np.full((K, K), 1.0 / K)
    pi = np.full(K, 1.0 / K)

    prev_ll = -np.inf
    converged = False

    for _ in range(n_iter):
        B = _emission_1d(x, means, stds)
        alpha, scale = _forward(B, A, pi)
        beta = _backward(B, A, scale)
        gamma = alpha * beta
        gamma /= gamma.sum(axis=1, keepdims=True) + 1e-300

        xi = np.zeros((T - 1, K, K))
        for t in range(T - 1):
            numer = alpha[t, :, None] * A * B[t + 1, None, :] * beta[t + 1, None, :]
            xi[t] = numer / (numer.sum() + 1e-300)

        ll = float(np.sum(np.log(scale + 1e-300)))
        if abs(ll - prev_ll) < tol:
            converged = True
            break
        prev_ll = ll

        pi = gamma[0] / (gamma[0].sum() + 1e-300)
        A = xi.sum(axis=0) / (gamma[:-1].sum(axis=0)[:, None] + 1e-300)
        for k in range(K):
            w = gamma[:, k]
            w_sum = w.sum() + 1e-300
            means[k] = np.dot(w, x) / w_sum
            stds[k] = np.sqrt(np.dot(w, (x - means[k]) ** 2) / w_sum + 1e-10)

    viterbi = _viterbi(B, A, pi)

    return {
        "means": means.tolist(),
        "stds": stds.tolist(),
        "transition_matrix": A.tolist(),
        "state_probs": gamma,
        "viterbi_path": viterbi,
        "log_likelihood": float(prev_ll),
        "converged": converged,
    }


# ======================================================================
# Multivariate implementation (diagonal covariance)
# ======================================================================


def _fit_multivariate(x, n_states, n_iter, tol, rng):
    T, D = x.shape
    K = n_states

    # Initialize means via k-means-like spread
    indices = np.linspace(0, T - 1, K, dtype=int)
    means = x[indices].copy()
    # Initialize diagonal covariances
    covars = np.tile(x.var(axis=0), (K, 1)) + 1e-6  # (K, D)
    A = np.full((K, K), 1.0 / K)
    pi = np.full(K, 1.0 / K)

    prev_ll = -np.inf
    converged = False

    for _ in range(n_iter):
        B = _emission_nd(x, means, covars)
        alpha, scale = _forward(B, A, pi)
        beta = _backward(B, A, scale)
        gamma = alpha * beta
        gamma /= gamma.sum(axis=1, keepdims=True) + 1e-300

        xi = np.zeros((T - 1, K, K))
        for t in range(T - 1):
            numer = alpha[t, :, None] * A * B[t + 1, None, :] * beta[t + 1, None, :]
            xi[t] = numer / (numer.sum() + 1e-300)

        ll = float(np.sum(np.log(scale + 1e-300)))
        if abs(ll - prev_ll) < tol:
            converged = True
            break
        prev_ll = ll

        pi = gamma[0] / (gamma[0].sum() + 1e-300)
        A = xi.sum(axis=0) / (gamma[:-1].sum(axis=0)[:, None] + 1e-300)
        for k in range(K):
            w = gamma[:, k]
            w_sum = w.sum() + 1e-300
            means[k] = (w[:, None] * x).sum(axis=0) / w_sum
            diff = x - means[k]
            covars[k] = (w[:, None] * diff ** 2).sum(axis=0) / w_sum + 1e-10

    viterbi = _viterbi(B, A, pi)

    return {
        "means": means.tolist(),
        "covariances": covars.tolist(),
        "transition_matrix": A.tolist(),
        "state_probs": gamma,
        "viterbi_path": viterbi,
        "log_likelihood": float(prev_ll),
        "converged": converged,
    }


# ======================================================================
# Emission helpers
# ======================================================================


def _emission_1d(x: np.ndarray, means: np.ndarray, stds: np.ndarray) -> np.ndarray:
    """Univariate Gaussian emission probabilities."""
    T = len(x)
    K = len(means)
    B = np.zeros((T, K))
    for k in range(K):
        B[:, k] = np.exp(-0.5 * ((x - means[k]) / stds[k]) ** 2) / (
            stds[k] * np.sqrt(2 * np.pi)
        )
    return B + 1e-300


def _emission_nd(x: np.ndarray, means: np.ndarray, covars: np.ndarray) -> np.ndarray:
    """Multivariate diagonal Gaussian emission probabilities."""
    T, D = x.shape
    K = len(means)
    B = np.zeros((T, K))
    for k in range(K):
        diff = x - means[k]  # (T, D)
        # log p = -0.5 * sum_d [(x_d - mu_d)^2 / var_d + log(var_d)] - D/2 * log(2pi)
        log_p = -0.5 * np.sum(diff ** 2 / covars[k] + np.log(covars[k]), axis=1)
        log_p -= 0.5 * D * np.log(2 * np.pi)
        B[:, k] = np.exp(log_p - log_p.max())  # numerical stability
    # Re-normalize per row to avoid underflow
    B = B / (B.sum(axis=1, keepdims=True) + 1e-300)
    return B + 1e-300


# ======================================================================
# Forward-backward + Viterbi (shared)
# ======================================================================


def _forward(B: np.ndarray, A: np.ndarray, pi: np.ndarray):
    """Scaled forward algorithm."""
    T, K = B.shape
    alpha = np.zeros((T, K))
    scale = np.zeros(T)
    alpha[0] = pi * B[0]
    scale[0] = alpha[0].sum()
    alpha[0] /= scale[0] + 1e-300
    for t in range(1, T):
        alpha[t] = (alpha[t - 1] @ A) * B[t]
        scale[t] = alpha[t].sum()
        alpha[t] /= scale[t] + 1e-300
    return alpha, scale


def _backward(B: np.ndarray, A: np.ndarray, scale: np.ndarray):
    """Scaled backward algorithm."""
    T, K = B.shape
    beta = np.zeros((T, K))
    beta[-1] = 1.0
    for t in range(T - 2, -1, -1):
        beta[t] = A @ (B[t + 1] * beta[t + 1])
        beta[t] /= scale[t + 1] + 1e-300
    return beta


def _viterbi(B: np.ndarray, A: np.ndarray, pi: np.ndarray) -> np.ndarray:
    """Viterbi decoding."""
    T, K = B.shape
    log_A = np.log(A + 1e-300)
    log_B = np.log(B + 1e-300)
    log_pi = np.log(pi + 1e-300)

    V = np.zeros((T, K))
    ptr = np.zeros((T, K), dtype=int)
    V[0] = log_pi + log_B[0]
    for t in range(1, T):
        for k in range(K):
            trans = V[t - 1] + log_A[:, k]
            ptr[t, k] = int(np.argmax(trans))
            V[t, k] = trans[ptr[t, k]] + log_B[t, k]

    path = np.zeros(T, dtype=int)
    path[-1] = int(np.argmax(V[-1]))
    for t in range(T - 2, -1, -1):
        path[t] = ptr[t + 1, path[t + 1]]
    return path
