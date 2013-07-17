from .. syntax.helpers import unwrap_constant 
from transform import Transform 


class IndexifyAdverbs(Transform):
  """
  Take all the adverbs whose parameterizing functions assume they 
  get fed slices of input data and turn them into version which take explicit
  input indices
  """
  _indexed_fn_cache = {}
  def indexify_fn(self, fn, k):
    """
    Take a function whose last k values are slices through input data 
    and transform it into a function which explicitly extracts its arguments
    """  
    
    # do I need fn.version *and* fn.copied_by? 
    key = (fn.name, fn.copied_by, fn.version, k)
    if key in self._indexed_fn_cache:
      return self._indexed_fn_cache[key]
    value_args = fn
  
  def transform_AllPairs(self, expr):
    axis = unwrap_constant(expr.axis)
    dimsizes = [self.shape(arg, axis) for arg in expr.args]
    