"""
The tests of pyrep, launched with run_tests.py.
"""
import os


def get_available_tests():
    """
    Lists the test files of this directory.

    :Returns:
        #. names (list): The file names of the tests, without the package file.
    """
    p, fname = os.path.split(os.path.abspath(__file__))
    return [f for f in os.listdir(p) if os.path.isfile(os.path.join(p, f))
                                        and  f.endswith(".py") 
                                        and not f.endswith(".pyc")
                                        and not f.startswith("__init__")]
