import copy

import adverbs
import array_type
import closure_type
import config
import names
import syntax

from collect_vars import collect_var_names as free_vars
from core_types import Int32
from syntax_visitor import SyntaxVisitor
from transform import Transform


class FindAdverbs(SyntaxVisitor):
  def __init__(self):
    self.has_adverbs = False

  def visit_Map(self, expr):
    self.has_adverbs = True

  def visit_Reduce(self, expr):
    self.has_adverbs = True

  def visit_Scan(self, expr):
    self.has_adverbs = True

  def visit_AllPairs(self, expr):
    assert False, \
        "Expected AllPairs operators to have been lowered into Maps"

class TileableAdverbsTagger(SyntaxVisitor):
  def __init__(self):
    self.adverbs_seen = 0

  def get_fn(self, maybe_clos):
    if isinstance(maybe_clos, syntax.Closure):
      return maybe_clos.fn
    else:
      return maybe_clos

  # We don't tile adverbs inside control flow for now.
  def visit_If(self, stmt):
    return

  def visit_While(self, smt):
    return

  def visit_Map(self, expr):
    if self.num_adverbs == 0:
      nested_counter = TileableAdverbsTagger()
      nested_counter.visit_fn(self.get_fn(expr.fn))
      self.num_adverbs = nested_counter.num_adverbs + 1

  def visit_Reduce(self, expr):
    if self.num_adverbs == 0:
      nested_counter = TileableAdverbsTagger()
      nested_counter.visit_fn(self.get_fn(expr.fn))
      self.num_adverbs = nested_counter.num_adverbs + 1

  def visit_Scan(self, expr):
    if self.num_adverbs == 0:
      nested_counter = TileableAdverbsTagger()
      nested_counter.visit_fn(self.get_fn(expr.fn))
      self.num_adverbs = nested_counter.num_adverbs + 1

  def visit_AllPairs(self, expr):
    assert False, \
        "Expected AllPairs operators to have been lowered into Maps"

class AdverbArgs():
  def __init__(self, fn=None, args=None, axis=0, combine=None, init=None,
               emit=None):
    self.fn = fn
    self.args = args
    self.axis = axis
    self.combine = combine
    self.init = init
    self.emit = emit

class TileAdverbs(Transform):
  def __init__(self):
    Transform.__init__(self)
    self.adverbs_visited = []
    self.adverb_args = []
    self.expansions = {}
    self.exp_stack = []
    self.type_env_stack = []

    # For now, we'll assume that no closure variables have the same name.
    self.closure_vars = {}

    self.num_tiles = 0

  def pre_apply(self, fn):
    if config.print_functions_before_tiling:
      print 
      print "BEFORE TILING"
      print "-----------------"
      print fn
    return fn

  def push_exp(self, adv, adv_args):
    self.exp_stack.append(self.expansions)
    self.expansions = copy.deepcopy(self.expansions)
    self.adverbs_visited.append(adv)
    self.adverb_args.append(adv_args)

  def pop_exp(self):
    self.expansions = self.exp_stack.pop()
    self.adverbs_visited.pop()
    self.adverb_args.pop()

  def push_type_env(self, type_env):
    self.type_env_stack.append(self.type_env)
    self.type_env = type_env

  def pop_type_env(self):
    old_type_env = self.type_env
    self.type_env = self.type_env_stack.pop()
    return old_type_env

  def get_expansions(self, arg):
    if arg in self.expansions:
      return self.expansions[arg]
    else:
      return []

  def get_closure_arg(self, closure_elt):
    if isinstance(closure_elt, syntax.ClosureElt):
      if isinstance(closure_elt.closure, syntax.Closure):
        return closure_elt.closure.args[closure_elt.index]
      elif isinstance(closure_elt.closure, syntax.Var):
        closure = self.closure_vars[closure_elt.closure.name]
        return closure.args[closure_elt.index]
      else:
        assert False, "Unknown closure type for closure elt %s" % closure_elt
    elif isinstance(closure_elt, syntax.Var):
      return closure_elt
    else:
      assert False, "Unknown closure closure elt type %s" % closure_elt

  def get_num_expansions_at_depth(self, arg, depth):
    exps = self.get_expansions(arg)

    for i,v in enumerate(exps):
      if v >= depth:
        return max(i-1,0)

    return len(exps)

  def gen_unpack_tree(self, adverb_tree, depths, v_names, block, type_env):
    def order_args(depth):
      cur_depth_args = []
      other_args = []
      for arg in v_names:
        arg_exps = self.get_expansions(arg)
        if depth in arg_exps:
          cur_depth_args.append(arg)
        else:
          other_args.append(arg)
      return (cur_depth_args, other_args)

    def gen_unpack_fn(depth_idx, arg_order):
      if depth_idx >= len(depths):
        # For each stmt in body, add its lhs free vars to the type env
        inner_type_env = copy.copy(type_env)
        return_t = Int32 # Dummy type
        for s in block:
          if isinstance(s, syntax.Assign):
            lhs_names = free_vars(s.lhs)
            lhs_types = [type_env[name] for name in lhs_names]
            for name, t in zip(lhs_names, lhs_types):
              inner_type_env[name] = t
          elif isinstance(s, syntax.Return):
            if isinstance(s.value, str):
              return_t = type_env[s.value.name]
            else:
              return_t = s.value.type

        # The innermost function always uses all the variables
        print type_env
        print inner_type_env
        fn = syntax.TypedFn(name = names.fresh("inner_block"),
                            arg_names = v_names,
                            body = block,
                            input_types = [type_env[arg] for arg in arg_order],
                            return_type = return_t,
                            type_env = inner_type_env)
        return fn
      else:
        # Get the current depth
        depth = depths[depth_idx]

        # Order the arguments for the current depth, i.e. for the nested fn
        cur_arg_names, fixed_arg_names = order_args(depth)
        nested_arg_names = fixed_arg_names + cur_arg_names

        # Make a type env for this function based on the number of expansions
        # left for each arg
        new_type_env = {}
        adv_args = self.adverb_args[depth_idx]
        new_adverb = adverb_tree[depth_idx](fn = adv_args.fn,
                                            args = adv_args.args,
                                            axis = adv_args.axis)
        # Increase the rank of each arg by the number of nested expansions
        # (i.e. the expansions of that arg that occur deeper in the nesting)
        for arg in nested_arg_names:
          exps = self.get_expansions(arg)
          rank_increase = 0
          for i, e in enumerate(exps):
            if e >= depth:
              rank_increase = len(exps) - i
              break
          new_type_env[arg] = \
              array_type.increase_rank(type_env[arg], rank_increase)

        cur_arg_types = [new_type_env[arg] for arg in cur_arg_names]
        fixed_arg_types = [new_type_env[arg] for arg in fixed_arg_names]

        # Generate the nested function with the proper arg order and wrap it
        # in a closure
        nested_fn = gen_unpack_fn(depth_idx+1, nested_arg_names)
        nested_args = [syntax.Var(name, type = t)
                       for name, t in zip(cur_arg_names, cur_arg_types)]
        nested_fixed_args = \
            [syntax.Var(name, type = t)
             for name, t in zip(fixed_arg_names, fixed_arg_types)]
        closure_t = closure_type.make_closure_type(nested_fn,
                                                   fixed_arg_types)
        nested_closure = syntax.Closure(nested_fn, nested_fixed_args,
                                        type=closure_t)

        # Make an adverb that wraps the nested fn
        new_adverb.fn = nested_closure
        new_adverb.args = nested_args
        return_t = nested_fn.return_type
        if isinstance(new_adverb, adverbs.Reduce):
          new_adverb.combine = adv_args.combine
          new_adverb.init = adv_args.init
        else:
          return_t = array_type.increase_rank(nested_fn.return_type, 1)
        new_adverb.type = return_t

        # Add the adverb to the body of the current fn and return the fn
        arg_types = [new_type_env[arg] for arg in arg_order]
        fn = syntax.TypedFn(name = names.fresh("intermediate_depth"),
                            arg_names = arg_order,
                            body = [syntax.Return(new_adverb)],
                            input_types = arg_types,
                            return_type = return_t,
                            type_env = new_type_env)
        return fn

    return gen_unpack_fn(0, v_names)

  def get_depths_list(self, v_names):
    depths = set()
    for name in v_names:
      for e in self.get_expansions(name):
        depths.add(e)
    depths = list(depths)
    depths.sort()
    return depths

  def transform_Assign(self, stmt):
    if isinstance(stmt.rhs, syntax.Closure):
      self.closure_vars[stmt.lhs.name] = stmt.rhs

    if isinstance(stmt.rhs, adverbs.Adverb):
      new_rhs = self.transform_expr(stmt.rhs)
      stmt.lhs.type = new_rhs.type
      self.type_env[stmt.lhs.name] = stmt.lhs.type
      return syntax.Assign(stmt.lhs, new_rhs)
    elif len(self.adverbs_visited) > 0:
      fv_names = free_vars(stmt.rhs)
      depths = self.get_depths_list(fv_names)
      map_tree = [adverbs.Map for _ in depths]
      inner_body = [stmt, syntax.Return(stmt.lhs)]
      nested_args, unpack_fn = \
          self.gen_unpack_tree(map_tree, depths, fv_names, inner_body,
                               self.fn.type_env)
      new_rhs = syntax.Call(unpack_fn, nested_args)
      stmt.lhs.type = new_rhs.type
      self.type_env[stmt.lhs.name] = new_rhs.type
      return syntax.Assign(stmt.lhs, new_rhs)
    else:
      # Do nothing if we're not inside a nesting of tiled adverbs
      return stmt

  def transform_Return(self, stmt):
    if isinstance(stmt.value, adverbs.Adverb):
      return syntax.Return(self.transform_expr(stmt.value))
    stmt.value.type = self.type_env[stmt.value.name]
    return stmt

  def transform_Map(self, expr):
    self.num_tiles += 1

    depth = len(self.adverbs_visited)
    closure = expr.fn
    closure_args = []
    fn = closure
    if isinstance(fn, syntax.Closure):
      closure_args = closure.args
      fn = closure.fn

    self.push_exp(adverbs.Map, AdverbArgs(expr.fn, expr.args, expr.axis))
    for fn_arg, adverb_arg in zip(fn.arg_names[:len(closure_args)],
                                  closure_args):
      name = self.get_closure_arg(adverb_arg).name
      new_expansions = copy.deepcopy(self.get_expansions(name))
      self.expansions[fn_arg] = new_expansions
    for fn_arg, adverb_arg in zip(fn.arg_names[len(closure_args):], expr.args):
      new_expansions = copy.deepcopy(self.get_expansions(adverb_arg.name))
      new_expansions.append(depth)
      self.expansions[fn_arg] = new_expansions

    new_fn = syntax.TypedFn
    depths = self.get_depths_list(fn.arg_names)
    find_adverbs = FindAdverbs()
    find_adverbs.visit_fn(fn)

    if find_adverbs.has_adverbs:
      arg_names = list(fn.arg_names)
      input_types = []
      self.push_type_env(fn.type_env)
      for arg, t in zip(arg_names, fn.input_types):
        new_type = array_type.increase_rank(t, len(self.get_expansions(arg)))
        input_types.append(new_type)
        self.type_env[arg] = new_type
      exps = self.get_depths_list(fn.arg_names)
      rank_inc = 0
      for i, exp in enumerate(exps):
        if exp >= depth:
          rank_inc = i
          break
      return_t = array_type.increase_rank(expr.type, rank_inc)
      new_fn = syntax.TypedFn(name = names.fresh("expanded_map_fn"),
                              arg_names = arg_names,
                              body = self.transform_block(fn.body),
                              input_types = input_types,
                              return_type = return_t,
                              type_env = self.pop_type_env())
      new_fn.has_tiles = True
    else:
      new_fn = self.gen_unpack_tree(self.adverbs_visited, depths, fn.arg_names,
                                    fn.body, fn.type_env)

    axes = [self.get_num_expansions_at_depth(arg.name, depth) + expr.axis
            for arg in expr.args]
    for arg, t in zip(expr.args, new_fn.input_types[len(closure_args):]):
      arg.type = t
    return_t = new_fn.return_type
    if isinstance(closure, syntax.Closure):
      for c_arg, t in zip(closure.args, new_fn.input_types):
        c_arg.type = t
      closure_arg_types = [arg.type for arg in closure.args]
      closure.fn = new_fn
      closure.type = closure_type.make_closure_type(new_fn, closure_arg_types)
      new_fn = closure
    self.pop_exp()
    return adverbs.TiledMap(fn = new_fn, args = expr.args, axes = axes,
                            type = return_t)

  # For now, reductions end the tiling chain.
  def transform_Reduce(self, expr):
    self.num_tiles += 1

    depth = len(self.adverbs_visited)
    closure = expr.fn
    closure_args = []
    fn = closure
    if isinstance(fn, syntax.Closure):
      closure_args = closure.args
      fn = closure.fn
    self.push_exp(adverbs.Reduce, AdverbArgs(combine = expr.combine,
                                             init = expr.init,
                                             fn = expr.fn,
                                             args = expr.args,
                                             axis = expr.axis))
    for fn_arg, adverb_arg in zip(fn.arg_names[:len(closure_args)],
                                  closure_args):
      name = self.get_closure_arg(adverb_arg)
      new_expansions = copy.deepcopy(self.get_expansions(name))
      self.expansions[fn_arg] = new_expansions
    for fn_arg, adverb_arg in zip(fn.arg_names[len(closure_args):], expr.args):
      new_expansions = copy.deepcopy(self.get_expansions(adverb_arg.name))
      new_expansions.append(depth)
      self.expansions[fn_arg] = new_expansions

    depths = self.get_depths_list(fn.arg_names)
    new_fn = self.gen_unpack_tree(self.adverbs_visited, depths,
                                  fn.arg_names,
                                  fn.body,
                                  fn.type_env)

    axes = [self.get_num_expansions_at_depth(arg.name, depth) + expr.axis
            for arg in expr.args]
    for arg, t in zip(expr.args, new_fn.input_types[len(closure_args):]):
      arg.type = t
    init = expr.init # Initial value lifted to proper shape in lowering
    if len(depths) > 1:
      depths.remove(depth)
      self.push_exp(None, None)
      for arg in expr.combine.arg_names:
        self.expansions[arg] = depths
      combine_maps = [adverbs.Map for _ in depths]
      new_combine = self.gen_unpack_tree(combine_maps, depths,
                                         expr.combine.arg_names,
                                         expr.combine.body,
                                         expr.combine.type_env)
      self.pop_exp()
    else:
      new_combine = expr.combine
    return_t = new_fn.return_type
    if isinstance(closure, syntax.Closure):
      for c_arg, t in zip(closure.args, new_fn.input_types):
        c_arg.type = t
      closure_arg_types = [arg.type for arg in closure.args]
      closure.fn = new_fn
      closure.type = closure_type.make_closure_type(new_fn, closure_arg_types)
      new_fn = closure
    self.pop_exp()
    return adverbs.TiledReduce(fn = new_fn,
                               combine = new_combine,
                               init = init,
                               args = expr.args,
                               axes = axes,
                               type = return_t)

  # TODO: Tiling scans should be very similar to tiling reductions.
  #def transform_Scan(self, expr):

  def post_apply(self, fn):
    fn.has_tiles = self.num_tiles > 0
    fn.num_tiles = self.num_tiles
    if config.print_tiled_adverbs:
      print 
      print "DONE WITH TILING"
      print "-----------------"
      print fn
    return fn
