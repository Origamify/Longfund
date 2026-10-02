"""Shared source: data provider and risk math. The entry point
(longfund.py at the repo root) imports from here."""

import os

# Pin BLAS-backed threads to 1 BEFORE numpy loads anywhere: every array here
# is tiny (single-stock bars), and scipy-openblas's spinning thread pool on
# many-core boxes slows small-op loops badly (measured: 1,396s unpinned vs
# 1.3s pinned). setdefault — an explicit env wins.
for _var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_var, "1")
