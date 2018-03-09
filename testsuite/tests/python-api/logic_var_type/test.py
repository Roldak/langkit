"""
Test that LogiVarType bindings in the Python API are properly working.
"""

from __future__ import absolute_import, division, print_function

import os.path
import sys

from langkit.diagnostics import Diagnostics
from langkit.dsl import (ASTNode, Field, LogicVarType, Token as TokenType,
                         UserField)
from langkit.expressions import langkit_property
from langkit.parsers import Grammar, Tok

from lexer_example import Token
from utils import build_and_run, emit_and_print_errors


Diagnostics.set_lang_source_dir(os.path.abspath(__file__))


def run_test(title, run_main):
    # Each time we print something, make sure we flush it so that output from
    # subprocesses is interleaved in a deterministic way.

    print(title)
    print('-' * len(title))
    sys.stdout.flush()

    class FooNode(ASTNode):
        var_field = UserField(type=LogicVarType, public=True)

        @langkit_property(public=True, return_type=LogicVarType)
        def var(v=LogicVarType):
            return v

    class Example(FooNode):
        tok = Field(type=TokenType)

    grammar = Grammar('main_rule')
    grammar.add_rules(
        main_rule=Example(Tok(Token.Example, keep=True)),
    )

    if run_main:
        build_and_run(grammar, 'main.py', library_fields_all_public=True)
    else:
        emit_and_print_errors(grammar)
    sys.stdout.flush()


# First, check that equation types in public properties are rejected
run_test('Emit with expected errors', False)

# Then check that the library can be generated and used from Python when we
# force all properties to be public.
run_test('Build and run:', True)

print('Done')