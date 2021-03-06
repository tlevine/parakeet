Parakeet
====

Parakeet is a runtime accelerator for an array-oriented subset of Python. 
If you're doing a lot of number crunching in Python, 
Parakeet may be able to significantly speed up your code. 


To accelerate a function, wrap it with Parakeet's **@jit** decorator:

```python 
import numpy as np 
from parakeet import jit 

x = np.array([1,2,3])
y = np.tanh(x * alpha) + beta
   
@jit
def fast(x, alpha = 0.5, beta = 0.3):
  return np.tanh(x * alpha) + beta 
   
@jit 
def loopy(x, alpha = 0.5, beta = 0.3):
  y = np.empty_like(x, dtype = float)
  for i in xrange(len(x)):
    y[i] = np.tanh(x[i] * alpha) + beta
  return y
     
@jit
def comprehension(x, alpha = 0.5, beta = 0.3):
  return np.array([np.tanh(xi*alpha) + beta for xi in x])
  
assert np.allclose(fast(x), y)
assert np.allclose(loopy(x), y)
assert np.allclose(comprehension(x), y)

```



Install
====
You should be able to install Parakeet from its [PyPI package](https://pypi.python.org/pypi/parakeet/) by running:

    pip install parakeet


Dependencies
====

Parakeet is written for Python 2.7 (sorry internet) and depends on:

* [treelike](https://github.com/iskandr/treelike)
* [nose](https://nose.readthedocs.org/en/latest/) for unit tests
* [NumPy and SciPy](http://www.scipy.org/install.html)

Optional (if using the LLVM backend):

* [llvmpy](http://www.llvmpy.org/#quickstart)



How does it work? 
====
Your untyped function gets used as a template from which multiple *type specializations* are generated 
(for each distinct set of input types). 
These typed functions are then churned through many optimizations before finally getting translated into native code. 

More information
===

  * Read more about Parakeet on the [project website](http://www.parakeetpython.com) 
  * Ask questions on the [discussion group](http://groups.google.com/forum/#!forum/parakeet-python)
  * Watch the [Parakeet presentation](https://vimeo.com/73895275) from this year's [PyData Boston](http://pydata.org/bos2013), look at the [HotPar slides](https://www.usenix.org/conference/hotpar12/parakeet-just-time-parallel-accelerator-python) from last year 
  * Contact the [main developer](http://www.rubinsteyn.com) directly



Supported language features
====

Parakeet cannot accelerate arbitrary Python code, it only supports a limited subset of the language:

  * Scalar operations (i.e. "x + 3 * y")
  * Control flow (if-statements, loops, etc...)
  * Nested functions and lambdas
  * Tuples
  * Slices
  * NumPy array expressions (i.e. "x[1:, :] + 2 * y[:-1, ::2]")
  * NumPy array constructors (i.e. np.ones, np.empty, etc..)
  * NumPy ufuncs (i.e. np.sin, np.exp, etc..)
  * List literals (interpreted as array construction)
  * List comprehensions (interpreted as array comprehensions)
  * Parakeet's "adverbs" (higher order array operations like parakeet.map, parakeet.reduce)

Backends
===
Parakeet currently supports compilation to sequential C, multi-core C with OpenMP (default), or LLVM (deprecated). To switch between these options change `parakeet.config.backend` to one of:
  * "c": lowers all parallel operators to loops, compile sequential code with gcc
  * "openmp": also compiles with gcc, but parallel operators run across multiple cores (default)
  * "cuda": launch parallel operations on the GPU (experimental)
  * "llvm": older backend, has fallen behind and some programs may not work


