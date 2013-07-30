from parakeet import jit 
from testing_helpers import run_local_tests, expect

@jit 
def mod(x,y):
    return x % y

def run_mod(x, y):
  expect(mod, [x,y], x%y)

def test_mod_positive():
  run_mod(4,4)
  run_mod(4,5)
  run_mod(5,4)

def test_mod_1st_negative():
  run_mod(-4,4)
  run_mod(-4,5)
  run_mod(-5,4)

def test_mod_2nd_negative():
  run_mod(4,-4)
  run_mod(4,-5)
  run_mod(5,-4)


def test_mod_both_negative():
  run_mod(-4,-4)
  run_mod(-4,-5)
  run_mod(-5,-4)

if __name__ == '__main__':
  run_local_tests()
