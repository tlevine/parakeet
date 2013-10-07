

from .. import ndtypes 
from .. ndtypes import ArrayT, Int64, elt_type, empty_tuple_t, TupleT 
from .. frontend import macro, jit, typed_macro 
from .. syntax import (Attribute, Tuple, Ravel, Shape, Reshape, TypeValue, Transpose, Const)
from .. syntax.helpers import const_int, zero_i64 


@macro
def transpose(x):
  return Transpose(x)

@macro 
def ravel(x):
  return Ravel(x)
  
@macro 
def reshape(x):
  return Reshape(x)


@typed_macro 
def get_elt_type(x):
  return TypeValue(ndtypes.elt_type(x.type))
  
@typed_macro
def itemsize(xt):
  return const_int(elt_type(xt.type).nbytes)
  
@typed_macro 
def rank(xt):
  return const_int(xt.type.rank) 

@typed_macro 
def size(xt, axis = None):
  if axis is None: 
    axis = zero_i64
  assert isinstance(axis, Const), "Axis argument to 'size' must be a constant, given %s" % axis
  assert axis.value == 0, "Calling 'size' along axes other than 0 not yet supported, given %s" % axis
  if isinstance(xt.type, ArrayT):
    return Attribute(xt, 'size', type = Int64)
  elif isinstance(xt.type, TupleT):
    return const_int(len(xt.type.elt_types))
  else:
    return const_int(1)

@jit 
def fill(x, v):
  for i in range(len(x)):
    x[i] = v 
 

@macro  
def shape(x):
  return Shape(x)


@jit 
def diff(x):
  """
  TODO:
    - axis selection
    - preserve size by filling with zeros
    - allow n'th differences by recursion
  """
  return x[1:] - x[:-1]
