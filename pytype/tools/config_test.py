"""Tests for config.py."""

import textwrap
import unittest

from pytype import file_utils
from pytype.tools import config


# TODO(rechen): How can we create and test a symlink loop?
class TestFindConfigFile(unittest.TestCase):
  """Tests for config.find_config_file."""

  def test_find(self):
    with file_utils.Tempdir() as d:
      f = d.create_file('setup.cfg')
      self.assertEqual(config.find_config_file(d.path), f)

  def test_find_from_file(self):
    with file_utils.Tempdir() as d:
      f1 = d.create_file('setup.cfg')
      f2 = d.create_file('some.py')
      self.assertEqual(config.find_config_file(f2), f1)

  def test_in_parent(self):
    with file_utils.Tempdir() as d:
      f = d.create_file('setup.cfg')
      path = d.create_directory('foo')
      self.assertEqual(config.find_config_file(path), f)

  def test_custom_name(self):
    with file_utils.Tempdir() as d:
      f = d.create_file('rainbow.unicorns')
      self.assertEqual(config.find_config_file(d.path, 'rainbow.unicorns'), f)

  def test_multiple_configs(self):
    with file_utils.Tempdir() as d:
      f1 = d.create_file('setup.cfg')
      path = d.create_directory('foo')
      f2 = d.create_file('foo/setup.cfg')
      self.assertEqual(config.find_config_file(d.path), f1)
      self.assertEqual(config.find_config_file(path), f2)

  def test_no_config(self):
    with file_utils.Tempdir() as d:
      self.assertIsNone(
          config.find_config_file(d.path, 'no.file.should.have.this.name'))


class TestConfigSection(unittest.TestCase):

  def test_get(self):
    with file_utils.Tempdir() as d:
      f = d.create_file('setup.cfg', textwrap.dedent('''
        [test]
        k1 = v1
        k2 = v2
      '''))
      section = config.ConfigSection.create_from_file(
          f, 'test', {k: None for k in ('k1', 'k2')})
    self.assertEqual(section.get('k1'), 'v1')
    self.assertEqual(section.get('k2'), 'v2')
    self.assertIsNone(section.get('k3'))

  def test_get_empty(self):
    with file_utils.Tempdir() as d:
      f = d.create_file('setup.cfg', textwrap.dedent('''
        [test]
        k =
      '''))
      section = config.ConfigSection.create_from_file(f, 'test', {'k': None})
      self.assertEqual(section.get('k'), '')

  def test_no_file(self):
    self.assertIsNone(config.ConfigSection.create_from_file(
        '/does/not/exist.cfg', 'test', {}))

  def test_malformed_file(self):
    with file_utils.Tempdir() as d:
      f = d.create_file('setup.cfg', 'rainbow = unicorns')
      self.assertIsNone(config.ConfigSection.create_from_file(f, 'test', {}))

  def test_missing_section(self):
    with file_utils.Tempdir() as d:
      f = d.create_file('setup.cfg')
      self.assertIsNone(config.ConfigSection.create_from_file(f, 'test', {}))

  def test_keymap(self):
    with file_utils.Tempdir() as d:
      f = d.create_file('setup.cfg', textwrap.dedent('''
        [test]
        k = v
      '''))
      section = config.ConfigSection.create_from_file(
          f, 'test', {'k': lambda v: 2*v})
      self.assertEqual(section.get('k'), 'vv')


if __name__ == '__main__':
  unittest.main()