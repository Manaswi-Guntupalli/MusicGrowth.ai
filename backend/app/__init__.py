from __future__ import annotations

import contextlib
import io
import os
import sys
import types

import numpy as np

# Some locked-down Windows environments block numba JIT DLL loading.
# Disabling JIT keeps librosa feature extraction usable in local/dev mode.
os.environ.setdefault("NUMBA_DISABLE_JIT", "1")
os.environ.setdefault("NUMBA_DISABLE_CUDA", "1")


def _install_numba_compat_stub_if_needed() -> None:
	"""Install a tiny numba shim if native numba import is blocked by policy."""
	force_stub = os.getenv("MUSICGROWTH_FORCE_NUMBA_STUB", "0") == "1"

	if not force_stub:
		try:
			with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
				import numba  # noqa: F401
			return
		except Exception:
			pass

	stub = types.ModuleType("numba")

	def _decorator_passthrough(*args, **kwargs):
		if args and callable(args[0]) and len(args) == 1 and not kwargs:
			return args[0]

		def _wrapper(func):
			return func

		return _wrapper

	def _vectorize_stub(*args, **kwargs):
		if args and callable(args[0]) and len(args) == 1 and not kwargs:
			func = args[0]
			vec = np.vectorize(func)

			def _wrapped(*fargs, **fkwargs):
				out = vec(*fargs, **fkwargs)
				if fargs and np.isscalar(fargs[0]):
					try:
						return out.item()
					except Exception:
						return out
				return out

			return _wrapped

		def _factory(func):
			vec = np.vectorize(func)

			def _wrapped(*fargs, **fkwargs):
				out = vec(*fargs, **fkwargs)
				if fargs and np.isscalar(fargs[0]):
					try:
						return out.item()
					except Exception:
						return out
				return out

			return _wrapped

		return _factory

	stub.jit = _decorator_passthrough
	stub.njit = _decorator_passthrough
	stub.stencil = _decorator_passthrough
	stub.guvectorize = _decorator_passthrough
	stub.vectorize = _vectorize_stub
	stub.prange = range
	stub.config = types.SimpleNamespace(DISABLE_JIT=True)
	stub.__version__ = "0"

	sys.modules.setdefault("numba", stub)


_install_numba_compat_stub_if_needed()

