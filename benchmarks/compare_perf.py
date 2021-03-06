
from parakeet import jit
from numba import autojit, config 
config.print_function = False 
import numpy as np 

from timer import timer 


def compare_perf(fn, args, numba= True, cpython = True, 
                 extra = {}, 
                 backends = ('c', 'openmp', 'cuda'), 
                 suppress_output = True):
  
  parakeet_fn = jit(fn)
  name = fn.__name__
  parakeet_result = None
  numba_result = None 
  cpython_result = None 
  kwargs = {'suppress_stdout': suppress_output, 'suppress_stderr':suppress_output}
  for backend in backends:
    with timer('Parakeet (backend = %s) #1 -- %s' % (backend, name), **kwargs):
      parakeet_result = parakeet_fn(*args, _backend = backend)

    with timer('Parakeet (backend = %s) #2 -- %s' % (backend, name), **kwargs):
      parakeet_result = parakeet_fn(*args, _backend = backend)

  if numba:
    numba_fn = autojit(fn)
    with timer('Numba #1 -- %s' % name, **kwargs):
      numba_result = numba_fn(*args)

    with timer('Numba #2 -- %s' % name, **kwargs):
      numba_result = numba_fn(*args)

  if cpython:
    with timer('Python -- %s' % name, **kwargs):
      cpython_result = fn(*args)
  
  if parakeet_result is not None and cpython_result is not None:
      assert np.allclose(cpython_result, parakeet_result), \
        "Difference between Parakeet and CPython = %s" % \
        np.sum(np.abs(cpython_result - parakeet_result))
  
  if numba_result is not None and cpython_result is not None:
      assert np.allclose(cpython_result, numba_result), \
        "Difference between Numba and CPython = %s" % \
        np.sum(np.abs(cpython_result - numba_result))

  
  for name, impl in extra.iteritems():
    with timer("%s #1" % name, **kwargs):
      impl(*args)
    with timer("%s #2" % name, **kwargs):
      extra_result = impl(*args)
    if parakeet_result is not None:
      assert np.allclose(parakeet_result, extra_result), \
        "Difference between Parakeet and %s = %s" % \
        (name, np.sum(np.abs(parakeet_result - extra_result)))


