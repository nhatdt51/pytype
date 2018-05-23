#! /usr/bin/python -B
"""A convenience script to run tests in a module within the Pytype source tree.

Usage:

$> test_module.py MODULE [-o RESULTS_FILE] [-p] [-s]

MODULE is the fully qualified name of a test module within the Pytype source
tree. For example, to run tests in pytype/tests/test_functions.py, specify
the module name as pytype.tests.test_functions.

RESULTS_FILE is the optional path to a file to write the test results into.

By default, only failures are printed to stdout. To see passed tests as
well on stdout, specify the "-p" option.

Be default, failure stack traces are not printed to stdout. To see failure
stack traces on stdout, specify the "-s" option.
"""

from __future__ import print_function
import argparse
import os
import sys
import unittest

PYTYPE_SRC_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class StatsCollector(object):
  """A class which collects stats while running tests."""

  def __init__(self, options):
    self._options = options
    self.class_count = 0
    self.method_count = 0
    self.error_count = 0
    self.fail_count = 0
    self.unexpected_success_count = 0

  def add_class(self):
    self.class_count += 1

  def add_method(self, test_result):
    self.method_count += 1
    self.error_count += len(test_result.errors)
    self.fail_count += len(test_result.failures)
    self.unexpected_success_count += len(test_result.unexpectedSuccesses)

  def report(self):
    msg = "\nRan %s methods from %s classes.\n" % (
        self.method_count, self.class_count)
    msg += "Found %d errors\n" % self.error_count
    msg += "Found %d failures\n" % self.fail_count
    msg += "Found %s unexpected successes\n" % self.unexpected_success_count
    print(msg)
    if self._options.output_file:
      self._options.output_file.write(msg)


class ResultReporter(object):
  """A class which reports results of test runs."""

  def __init__(self, options, stats_collector):
    self._options = options
    self._stats_collector = stats_collector

  def _method_info(self, prefix, fq_method_name, group):
    common_msg = "%s: %s" % (prefix, fq_method_name)
    log_message = "%s\n%s" % (common_msg, group[0][1])
    print_message = log_message if self._options.print_st else common_msg
    return log_message, print_message

  def report_method(self, fq_method_name, test_result):
    self._stats_collector.add_method(test_result)
    ret_val = 0
    problems_list = [("ERROR", test_result.errors),
                     ("FAIL", test_result.failures),
                     ("UNEXPECTED PASS", test_result.unexpectedSuccesses)]
    for kind, problems in problems_list:
      if problems:
        log_msg, print_msg = self._method_info(kind, fq_method_name, problems)
        ret_val = 1
        # There can only be one kind of problem because a different test_result
        # object is used for each method.
        break
    if ret_val == 0:
      log_msg = "PASS: %s" % fq_method_name
      if self._options.print_passes:
        print(log_msg)
    else:
      print(print_msg)
    if self._options.output_file:
      self._options.output_file.write(log_msg + "\n")
    return ret_val

  def report_class(self, class_name):
    self._stats_collector.add_class()
    msg = "\nRunning test methods in class %s ..." % (
        self._options.fq_mod_name + "." + class_name)
    print(msg)
    if self._options.output_file:
      self._options.output_file.write(msg + "\n")

  def report_module(self):
    msg = "\nRunning tests in module %s ..." % self._options.fq_mod_name
    print(msg)
    if self._options.output_file:
      self._options.output_file.write(msg + "\n")


def parse_args():
  """Parse the command line options and return the result."""
  parser = argparse.ArgumentParser()
  parser.add_argument("fq_mod_name", type=str, metavar="FQ_MOD_NAME",
                      help="Fully qualified name of the test module to run.")
  parser.add_argument("-o", "--output", type=str,
                      help="Path to the results file.")
  parser.add_argument("-p", "--print_passes", action="store_true",
                      help="Print information about passing tests to stdout.")
  parser.add_argument("-s", "--print_st", action="store_true",
                      help="Print stack traces of failing tests to stdout.")
  return parser.parse_args()


def run_test_method(method_name, class_object, options, reporter):
  """Run a test method and return 0 on success, 1 on failure."""
  test_object = class_object(method_name)
  test_object.setUp()
  test_result = test_object.defaultTestResult()
  test_object.run(test_result)
  test_object.tearDown()
  fq_method_name = ".".join(
      [options.fq_mod_name, class_object.__name__, method_name])
  return reporter.report_method(fq_method_name, test_result)


def run_tests_in_class(class_object, options, reporter):
  """Run test methods in a class and return the number of failing methods.."""
  result = 0
  class_object.setUpClass()
  reporter.report_class(class_object.__name__)
  for method_name, method_object in class_object.__dict__.items():
    if callable(method_object) and method_name.startswith("test"):
      result += run_test_method(method_name, class_object, options,
                                reporter)
  class_object.tearDownClass()
  return result


def run_tests_in_module(mod_object, options, reporter):
  """Run test methods in a module and return the number of failing methods.."""
  reporter.report_module()
  result = 0
  for _, class_object in mod_object.__dict__.items():
    if (isinstance(class_object, type) and
        issubclass(class_object, unittest.TestCase)):
      result += run_tests_in_class(class_object, options, reporter)
  return result


def main():
  # We add path to the pytype source root at the beginning of sys.path so that
  # it gets picked up before other potential pytype installations present
  # already.
  sys.path = [PYTYPE_SRC_ROOT] + sys.path
  options = parse_args()
  mod_abs_path = os.path.join(
      PYTYPE_SRC_ROOT, options.fq_mod_name.replace(".", os.path.sep) + ".py")
  if not os.path.exists(mod_abs_path):
    sys.exit("Module %s not found." % options.fq_mod_name)
  if "." in options.fq_mod_name:
    fq_pkg_name, _ = options.fq_mod_name.rsplit(".", 1)
    mod_object = __import__(options.fq_mod_name, fromlist=[fq_pkg_name])
  else:
    mod_object = __import__(options.fq_mod_name)
  stats_collector = StatsCollector(options)
  reporter = ResultReporter(options, stats_collector)

  def run(output_file):
    options.output_file = output_file
    result = run_tests_in_module(mod_object, options, reporter)
    stats_collector.report()
    return result

  if options.output:
    with open(options.output, "w") as output_file:
      result = run(output_file)
  else:
    result = run(None)
  if result != 0:
    sys.exit(1)


if __name__ == "__main__":
  main()
