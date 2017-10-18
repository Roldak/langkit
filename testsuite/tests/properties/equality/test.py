"""
Check that the DSL equality operator tests for equivalence, not pointer
equality.
"""

from __future__ import absolute_import, division, print_function

import os.path

from langkit.diagnostics import Diagnostics
from langkit.dsl import ASTNode, Field, T
from langkit.envs import EnvSpec, add_env, add_to_env
from langkit.expressions import New, Self, langkit_property
from langkit.parsers import Grammar, List, Opt, Tok

from lexer_example import Token
from utils import build_and_run


Diagnostics.set_lang_source_dir(os.path.abspath(__file__))


class FooNode(ASTNode):
    pass


class Decl(FooNode):
    has_plus = Field()
    name = Field()
    items = Field()

    env_spec = EnvSpec(
        add_to_env(mappings=New(T.env_assoc, key=Self.name.symbol, val=Self)),
        add_env(),
    )

    @langkit_property(public=True, return_type=T.BoolType)
    def test_env(other=T.FooNode.entity):
        return Self.children_env.env_orphan == other.children_env.env_orphan


class Ref(FooNode):
    name = Field()


fg = Grammar('main_rule')
fg.add_rules(
    main_rule=List(fg.decl),
    decl=Decl(Opt('+').as_bool(),
              Tok(Token.Identifier, keep=True),
              '(', fg.ref_list, ')'),
    ref_list=List(fg.ref, empty_valid=True),
    ref=Ref(Tok(Token.Identifier, keep=True)),
)
build_and_run(fg, 'main.py')
print('Done')