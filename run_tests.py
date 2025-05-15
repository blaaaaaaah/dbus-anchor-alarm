import unittest
loader = unittest.TestLoader()

suite = loader.discover("tests", "*_test.py")

runner = unittest.TextTestRunner()
runner.run(suite)