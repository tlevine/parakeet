import __builtin__
import numpy as np 

from .. frontend.decorators import jit, macro, typed_macro 
from .. ndtypes import (TypeValueT, ScalarT, make_array_type, make_tuple_type, Float64, 
                        type_conv, ArrayT, TupleT, IntT, Int64) 
from .. syntax import (Range, Cast, AllocArray, TupleProj, Array )

from ..syntax.helpers import get_types, one_i64, zero_i64

from adverbs import imap 
from numpy_types import float64
from lib_helpers import _get_type, _get_shape    
from parakeet.ndtypes.core_types import combine_type_list

@macro
def arange(n, *xs, **kwds):
  if 'dtype' in kwds:
    elt_t = kwds['dtype']
    del kwds['dtype']
  else:
    elt_t = Int64
  assert len(kwds) == 0, "Unexpected keyword arguments to 'arange': %s" % kwds
  array_t = make_array_type(elt_t, 1) 
  count = __builtin__.len(xs)
  assert 0 <= count <= 2, "Too many args for range: %s" % ((n,) + tuple(xs))
  
  if count == 0:
    start = zero_i64 
    stop = n 
    step = one_i64 
  elif count == 1:
    start = n 
    stop = xs[0]
    step = one_i64 
  else:
    start = n 
    stop = xs[0]
    step = xs[1]
    
  if elt_t != Int64:
    start = Cast(start, type = elt_t)
    stop = Cast(stop, type = elt_t)
    step = Cast(step, type = elt_t)
  return Range(start, stop, step, type = array_t)
 

  

@typed_macro
def empty(shape, dtype = float64):
  elt_t = _get_type(dtype)
  assert isinstance(elt_t, ScalarT), "Array element type %s must be scalar" % (elt_t,)
  shape = _get_shape(shape)  
  rank = len(shape.type.elt_types)
  arr_t = make_array_type(elt_t, rank)
  return AllocArray(shape = shape, elt_type = elt_t, type = arr_t)

@jit 
def empty_like(x, dtype = None):
  if dtype is None:
    return empty(x.shape, x.dtype)
  else:
    return empty(x.shape, dtype)
  
@typed_macro  
def zeros(shape, dtype = float64):
  zero = dtype(0)
  return imap(lambda _: zero, shape)
  #return ConstArrayLike(shape = shape, value = zero)

@jit
def zeros_like(x, dtype = None):
  if dtype is None:
    dtype = x.dtype
  return zeros(x.shape, dtype)

@jit
def ones(shape, dtype = float64):
  one = dtype(1)
  return imap(lambda _: one, shape)

@jit
def ones_like(x, dtype = None):
  if dtype is None:
    dtype = x.dtype
  return ones(x.shape, dtype)

@jit
def copy(x):
  return [xi for xi in x]

 
@typed_macro
def array(value):
  if isinstance(value.type, ArrayT):
    return value 
  else:
    assert isinstance(value.type, TupleT), "Don't know how to make array from %s : %s" % (value, value.type)
    elt_types = value.type.elt_types
    assert all(isinstance(t, ScalarT) for t in elt_types), \
      "Can only make array from tuple of scalars, not %s : %s" % (value, value.type)
    elt_t = combine_type_list(value.type.elt_types)
    array_t = make_array_type(elt_t, 1)
    array_elts = []
    for i, tuple_elt_t in enumerate(value.type.elt_types):
      tuple_elt = TupleProj(value, i, type = tuple_elt_t)
      if tuple_elt_t != elt_t:
        tuple_elt = Cast(tuple_elt, type = elt_t)
      array_elts.append(tuple_elt)
    return Array(elts = tuple(array_elts), type = array_t)


