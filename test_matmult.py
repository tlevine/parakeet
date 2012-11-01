import parakeet as par 
from parakeet import sum, allpairs
from testing_helpers import  expect, expect_allpairs, run_local_tests

import numpy as np 
bool_vec = np.array([True, False, True, False, True])
int_vec = np.array([1,2,3,4,5])
float_vec = np.array([10.0, 20.0, 30.0, 40.0, 50.0])

vectors = [bool_vec, int_vec, float_vec]


def loop_dot(x,y):
  n = x.shape[0]
  result = x[0] * y[0]
  i = 1
  while i < n:
      result = result + x[i] * y[i]
      i = i + 1
  return result

def test_loopdot():
  expect_allpairs(loop_dot, np.dot, vectors)

def dot(x,y):
  return sum(x*y)

#def test_adverb_dot():
#  expect_allpairs(dot, np.dot, vectors)

def adverb_matmult(X,Y):
  return allpairs(dot, X, Y, axis = 0)

int_mat = np.reshape(np.arange(100), (10,10))
float_mat = np.sqrt(int_mat)
bool_mat = int_mat % 2

matrices = [int_mat, float_mat, bool_mat]

#def test_adverb_matmult():
#  expect_allpairs(adverb_matmult, np.dot, matrices)


def loop_matmult(X, Y, Z):
  n_rows, row_length = X.shape
  n_cols = Y.shape[1]  
#  result_shape = (n_rows, n_cols)
#  Z = zeros( (n_rows, n_cols), dtype = (X[0,0] * Y[0,0]).dtype)
  i = 0
  while i < n_rows:
    j = 0
    while j < n_cols:
      total = X[i, 0] * Y[0, j] 
      k = 1
      while k < row_length:
        total = total + X[i, k] * Y[k, j]
        k = k + 1
      Z[i, j] = total
      j = j + 1 
    i = i + 1
  return Z

def test_loop_matmult():
  for X in matrices:
    for Y in matrices:
      res = np.dot(X, Y)
      Z = np.zeros_like(res)
      expect(loop_matmult, [X,Y,Z], res)
      
if __name__ == '__main__':
  run_local_tests()
    