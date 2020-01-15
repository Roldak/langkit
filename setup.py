#! /usr/bin/env python

"""Setup configuration file for the Langkit framework."""

from __future__ import absolute_import, division, print_function

from distutils.cmd import Command
from distutils.command.install import install as InstallCommand
from distutils.core import setup

import os
import re
import subprocess
import sys


ROOT_DIR = os.path.dirname(__file__)

if ROOT_DIR != '':
    os.chdir(ROOT_DIR)


# todo RA22-015: Remove this once the transition to the concrete
# syntax is done.
class BuildLibpythonlang(Command):
    """
    The command for building libpythonlang.

    It's basically running `manage.py make -P` from inside the "contrib/python"
    directory.
    """
    description = 'Build libpythonlang'

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        print("Building libpythonlang...")

        old_dir = os.getcwd()
        os.chdir('contrib/python/')
        subprocess.call(['./manage.py', 'make', '-P'])
        os.chdir(old_dir)

        print("Done building libpythonlang!")


# todo RA22-015: Remove this once the transition to the concrete
# syntax is done.
class InstallLibpythonlang(Command):
    """
    The command for installing libpythonlang.

    It's basically running the `setup.py` script that was generated as part of
    the build process.
    """
    description = 'Install libpythonlang'

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        self.run_command('build_lpl')

        print("Installing libpythonlang...")

        old_dir = os.getcwd()
        os.chdir('contrib/python/build')

        # copy libpythonlang and langkit_support libs

        for pat in ('.*\.dll', '.*\.so', '.*\.so\.*', '.*\.dylib'):
            for root, dirnames, filenames in os.walk('lib'):
                for f in filter(lambda f: re.match(pat, f), filenames):
                    full_path = os.path.join(root, f)
                    self.copy_file(full_path, 'python/libpythonlang')

        # run python setup.py install

        os.chdir('python')
        env_with_langkit = os.environ.copy()
        env_with_langkit['PYTHONPATH'] = "{}:{}".format(
            old_dir, env_with_langkit.get('PYTHONPATH', '')
        )
        subprocess.call(
            [sys.executable, 'setup.py', 'install'],
            env=env_with_langkit
        )

        os.chdir(old_dir)

        print("Done installing libpythonlang!")


class InstallLangkit(InstallCommand):
    """
    The command for installing langkit and its dependencies.
    """

    # todo RA22-015: Remove this once the transition to the concrete
    # syntax is done.
    sub_commands = InstallCommand.sub_commands + [
        ('install_lpl', lambda self: True)
    ]


# Run the setup tools
setup(
    cmdclass={
        'build_lpl': BuildLibpythonlang,
        'install_lpl': InstallLibpythonlang,
        'install': InstallLangkit
    },
    name='Langkit',
    version='0.1-dev',
    author='AdaCore',
    author_email='report@adacore.com',
    url='https://www.adacore.com',
    description='A Python framework to generate language parsers',
    install_requires=['Mako', 'PyYAML', 'enum', 'enum34', 'funcy', 'docutils'],
    packages=['langkit',
              'langkit.expressions',
              'langkit.gdb',
              'langkit.lexer',
              'langkit.stylechecks',
              'langkit.utils'],
    package_data={'langkit': [
        'support/*.adb', 'support/*.ads', 'support/*.gpr',
        'templates/*.mako', 'templates/*/*.mako'
    ]},
    scripts=[os.path.join('scripts', 'create-project.py')]
)
