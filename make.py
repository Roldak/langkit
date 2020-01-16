"""
Helper script to build langkit and its dependencies.
"""

from __future__ import absolute_import, division, print_function

from contextlib import contextmanager

import argparse

import os
import shutil
import subprocess
import sys


from langkit.utils import add_search_path


parser = argparse.ArgumentParser(
    description='Helper script to build langkit and its dependencies'
)
parser.add_argument('--build-mode', default='dev')

subparsers = parser.add_subparsers()

build_parser = subparsers.add_parser('build')
build_parser.set_defaults(command='build')

setenv_parser = subparsers.add_parser('setenv')
setenv_parser.set_defaults(command='setenv')

install_parser = subparsers.add_parser('install')
install_parser.set_defaults(command='install')
install_parser.add_argument('prefix', type=str,
                            help='Where to install Langkit dependencies')
install_parser.add_argument('--gnat-install-dir', type=str, default=None,
                            help='Specify where GNAT is installed. If not'
                                 'provided, assume it is installed where '
                                 'Langkit must be installed.')
install_parser.add_argument('--gnatcoll-bindings-install-dir', type=str,
                            default=None,
                            help='Specify where GNATCOLL bindings are '
                                 'installed. If not provided, assume it is '
                                 'installed where Langkit must be installed.')
install_parser.add_argument('--libgpr-install-dir', type=str,
                            default=None,
                            help='Specify where libgpr is installed. If not '
                                 'provided, assume it is installed where '
                                 'Langkit must be installed.')


ROOT_DIR = os.path.dirname(__file__)

if ROOT_DIR != '':
    os.chdir(ROOT_DIR)

LIBPYTHONLANG_DIR = os.path.join('contrib', 'python')


@contextmanager
def in_dir(path):
    """
    Move the working directly to the given path for the span of this context
    manager.

    :type path: str
    """
    old_dir = os.getcwd()
    os.chdir(path)
    yield
    os.chdir(old_dir)


def pip_install(setup_dir):
    """
    Install the python package located in the given directory.

    :type setup_dir: str
    :raise CalledProcessError if installation terminates with non-zero status
    """
    with in_dir(setup_dir):
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '.'])


def copy_all_shared_libs(from_dir, destination, *patterns):
    """
    Copy all shared libraries from anywhere in a given source tree to a given
    destination folder.

    Only the libraries that satisfy the given simple patterns are copied.
    Given patterns must NOT be regular expressions, but simple strings.
    A library will match if the pattern is a substring of the library's name.

    :type from_dir: str
    :type destination: str
    :type patterns: *str
    """
    for root, _, filenames in os.walk(from_dir):
        for filename in filenames:
            if any(n in filename for n in patterns):
                if any(ext in filename for ext in (".so", ".dll", ".dylib")):
                    shutil.copy(os.path.join(root, filename), destination)


def manage(lang_dir, verb, build_mode, *add_args, **kwargs):
    """
    Run the manage.py script from of a Langkit-based language definition.

    :param str verb: 'generate', 'build', 'install', etc.
    :param str build_mode: 'dev' or 'prod'.
    :param str|None rpath: if set, defines the RPATH to include in built
        shared libraries.
    :param *str add_args: additional arguments to pass
    :raise CalledProcessError if 'manage.py' terminates with non-zero status
    """
    with in_dir(lang_dir):
        args = [sys.executable, 'manage.py', verb]
        args.extend(['--build-mode', build_mode])
        args.extend(add_args)

        rpath = kwargs.pop('rpath', None)
        if rpath is None:
            subprocess.check_call(args)
        else:
            args.append('--gargs="-R"')
            env = os.environ.copy()
            env['LD_RUN_PATH'] = rpath
            subprocess.check_call(args, env=env)


def build_language(lang_dir, build_mode, rpath=None):
    """
    Build a Langkit-based language.

    :param str lang_dir: The directory in which the 'manage.py' script lives.
    :param str build_mode: The build mode to use (dev or prod).
    :param str|None rpath: The rpath to include in the built shared objects.
        If set, replaces the default one.
    :raise CalledProcessError if build fails
    """
    manage(lang_dir, 'make', build_mode, '-P', rpath=rpath)


def install_language(lang_dir, lang_name, build_mode, prefix,
                     gnat_install, gnatcoll_bindings_install, libgpr_install):
    """
    Install a Langkit-based language and its python bindings.

    :param str lang_dir: The directory in which the 'manage.py' script lives.
    :param str lang_name: The full name of the language
        (e.g. libadalang, libpythonlang).
    :param str build_mode: The build mode to use (dev or prod).
    :param str prefix: Where to install the language.

    :param str gnat_install: The directory in which GNAT is installed.
    :param str gnatcoll_bindings_install: The directory in which GNATCOLL
        bindings are installed.
    :param str libgpr_install: The directory in which libgpr is installed.

    :raise CalledProcessError|OSError if build fails.
    """
    manage(lang_dir, 'install', build_mode, prefix)

    # Copy all necessary shared libraries in the python package, so that the
    # subsequent call to pip_install packages all of them.

    lang_python_dir = os.path.join(lang_dir, 'build', 'python')
    dest = os.path.join(lang_python_dir, lang_name)

    copy_all_shared_libs(gnat_install, dest, "gnat", "gnarl", "xmlada")
    copy_all_shared_libs(gnatcoll_bindings_install, dest, "gnatcoll")
    copy_all_shared_libs(libgpr_install, dest, "gpr")
    copy_all_shared_libs(prefix, dest, lang_name, "langkit_support")

    pip_install(lang_python_dir)


def build(args):
    """
    Build langkit and its dependencies.

    :type argparse.Namespace
    """
    # build Libpythonlang
    build_language(LIBPYTHONLANG_DIR, args.build_mode)


def setenv(args):
    """
    Make available Langkit and its dependencies.

    :type argparse.Namespace
    """
    # Set Libpythonlang env
    manage(LIBPYTHONLANG_DIR, 'setenv', args.build_mode)

    # Also add Langkit package to PYTHONPATH
    print(add_search_path('PYTHONPATH', os.path.abspath(ROOT_DIR)))


def install(args):
    """
    Install Langkit and its dependencies.

    :type argparse.Namespace
    """
    # install langkit
    pip_install('.')

    # build libpythonlang. Since we build it for installation, make sure to
    # set the RPATH to look for library in the current dir at run time.

    build_language(LIBPYTHONLANG_DIR, args.build_mode, rpath="$ORIGIN")

    # install libpythonlang

    install_dir = os.path.abspath(args.prefix)

    gnat_install_dir = (
        args.gnat_install_dir
        if args.gnat_install_dir is not None
        else install_dir
    )
    gnatcoll_bindings_install_dir = (
        args.gnatcoll_bindings_install_dir
        if args.gnatcoll_bindings_install_dir is not None
        else install_dir
    )
    libgpr_install_dir = (
        args.libgpr_install_dir
        if args.libgpr_install_dir is not None
        else install_dir
    )

    install_language(
        LIBPYTHONLANG_DIR, 'libpythonlang', args.build_mode, install_dir,
        gnat_install_dir, gnatcoll_bindings_install_dir, libgpr_install_dir
    )


if __name__ == '__main__':
    args = parser.parse_args()

    if args.command == 'build':
        build(args)
    elif args.command == 'setenv':
        setenv(args)
    elif args.command == 'install':
        install(args)
    else:
        raise NotImplementedError('Unhandled command {}'.format(args.command))
