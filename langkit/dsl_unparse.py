from __future__ import absolute_import, division, print_function

from funcy import keep

from langkit.passes import GlobalPass
import libpythonlang as lpl
from contextlib import contextmanager

templates = {}


class DSLWalker(object):
    ctx = lpl.AnalysisContext()

    class NoOpWalker(object):
        def __init__(self):
            pass

        def __getattr__(self, item):
            return self

        def __call__(self, *args, **kwargs):
            return self

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            return self

        def emit_comments(self):
            return ""

    @staticmethod
    def class_from_location(loc):
        if not loc:
            return DSLWalker.NoOpWalker()

        unit = DSLWalker.ctx.get_from_file(loc.file)
        class_def = unit.root.find(
            lambda n:
            n.is_a(lpl.ClassDef) and
            n.sloc_range.start.line == loc.line
        )

        if not class_def:
            return DSLWalker.NoOpWalker()

        return DSLWalker(class_def)

    def __init__(self, from_node):
        self.current_node = from_node
        self.last_token = from_node.token_start
        self.current_token = self.last_token

    @contextmanager
    def _with_current_node(self, new_node):
        old_node = self.current_node
        self.current_node = new_node
        self.current_token = new_node.token_start
        yield
        self.current_node = old_node
        self.current_token = new_node.token_end

    def property(self, prop):
        pname = prop._indexing_name

        fun_decl = self.current_node.find(
            lambda n: n.is_a(lpl.FuncDef) and n.f_name.text == pname
        )

        if fun_decl is not None:
            # property is defined with the following syntax:
            # @langkit_property(...)
            # def prop(x):
            #     v0 = Var(...)
            #     ...
            #     return ...
            self.last_token = fun_decl.token_start
            return self._with_current_node(fun_decl.f_body)

        assignment = self.current_node.find(
            lambda n:
            n.is_a(lpl.AssignStmt) and
            n.f_l_value.text == pname and
            n.f_r_values[0][0].is_a(lpl.CallExpr) and
            'property' in n.f_r_values[0][0].f_prefix.text.lower()
        )

        if assignment is not None:
            self.last_token = assignment.f_r_values.token_start
            content = assignment.f_r_values[0][0].f_suffix

            if content[0].f_expr.is_a(lpl.LambdaDef):
                # property is defined with the following syntax:
                # prop = *Property(lambda x: ...)
                return self._with_current_node(content[0].f_expr.f_expr)
            else:
                # property is defined with the following syntax:
                # prop = *Property(...)
                return self._with_current_node(content)

        raise LookupError("Could not find proprety {}".format(pname))

    def var_assignment(self, index):
        var_calls = self.current_node.findall(
            lambda n: n.is_a(lpl.CallExpr) and n.f_prefix.text == "Var"
        )
        return self._with_current_node(var_calls[index].f_suffix)

    def returned_expr(self):
        if self.current_node.parent.is_a(lpl.LambdaDef):
            return self._with_current_node(self.current_node)

        return_stmt = self.current_node.find(
            lambda n: n.is_a(lpl.ReturnStmt)
        )
        assert len(return_stmt.f_exprs) == 1
        return self._with_current_node(return_stmt.f_exprs[0])

    def call(self, fun_name):
        def matches(n):
            return n.is_a(lpl.CallExpr) and n.f_prefix.text == fun_name

        call_node = (
            self.current_node
            if matches(self.current_node)
            else self.current_node.find(matches)
        )

        return self._with_current_node(call_node)

    def method_call(self, method_name):
        def matches(n):
            if n.is_a(lpl.CallExpr):
                if n.f_prefix.is_a(lpl.DottedName):
                    return n.f_prefix.f_suffix.text == method_name
            return False

        call_node = (
            self.current_node
            if matches(self.current_node)
            else self.current_node.find(matches)
        )

        return self._with_current_node(call_node)

    def self_arg(self):
        assert self.current_node.is_a(lpl.CallExpr)
        assert self.current_node.f_prefix.is_a(lpl.DottedName)
        return self._with_current_node(self.current_node.f_prefix.f_prefix)

    def arg(self, index):
        assert self.current_node.is_a(lpl.CallExpr)
        return self._with_current_node(self.current_node.f_suffix[index])

    def missed_comments(self):
        cur_tok = self.current_token
        while self.last_token < cur_tok:
            token = self.last_token
            if token.kind == 'Comment':
                yield token.text
            self.last_token = self.last_token.next

    def emit_comments(self):
        return "".join("{}$hl".format(c) for c in self.missed_comments())

    def where(self):
        print(self.current_node)


def sf(strn):
    """
    Real string splicing in cpython.

    Usage:

    >>> a = 12
    >>> b = 15
    >>> r = range(5)
    >>> sf("${a - b} : ${', '.join(str(c) for c in r)}")

    :param basestring strn: The string to format, containing regular python
                            expressions in ${} blocks.
    :rtype: unicode
    """

    from mako.template import Template
    import inspect

    frame = inspect.stack()[1][0]
    if not templates.get(strn):
        t = templates[strn] = Template(
            "\n".join(map(str.strip, strn.splitlines()))
        )
    else:
        t = templates[strn]

    return t.render(**dict(frame.f_locals, **frame.f_globals))


def emit_rule(rule):
    from langkit.parsers import (
        _Transform, node_name, _Row, Opt, List, Or, _Token, NoBacktrack,
        _Extract, DontSkip, Skip, Null, Parser, resolve, Defer, Predicate,
        Discard
    )
    if isinstance(rule, _Transform):
        inner = emit_rule(rule.parser)
        if len(inner) > 50:
            return "{}($i$hl{}$d$hl)".format(node_name(rule.typ), inner)
        else:
            return "{}({})".format(node_name(rule.typ), inner)
    elif isinstance(rule, _Row):
        return " $sl".join(emit_rule(r) for r in rule.parsers)
    elif isinstance(rule, Opt):
        return (
            "?({})".format(emit_rule(rule.parser))
            if isinstance(rule.parser, _Row)
            else "?{}".format(emit_rule(rule.parser))
        )
    elif isinstance(rule, _Extract):
        return emit_rule(rule.parser)
    elif isinstance(rule, List):
        sep_str = ", {}".format(emit_rule(rule.sep)) if rule.sep else ""
        return "list{}({}{})".format(
            '+' if rule.empty_valid else '*', emit_rule(rule.parser), sep_str
        )
    elif isinstance(rule, Null):
        return "null({})".format(
            emit_rule(rule.type) if isinstance(rule.type, Parser)
            else node_name(rule.type)
        )
    elif isinstance(rule, Or):
        body = ' | '.join(emit_rule(r) for r in rule.parsers)
        if len(body) > 50:
            return "or($i$hl| {}$d$hl)".format(
                '$hl| '.join(emit_rule(r) for r in rule.parsers)
            )
        else:
            return "or({})".format(body)
    elif isinstance(rule, DontSkip):
        return "{}.dont_skip({})".format(
            emit_rule(rule.subparser),
            " ".join((emit_rule(resolve(d)) for d in rule.dontskip_parsers))
        )
    elif isinstance(rule, Skip):
        return "skip({})".format(node_name(rule.dest_node))
    elif isinstance(rule, _Token):
        if isinstance(rule._val, basestring):
            return '"{}"'.format(rule._val)
        else:
            return "@{}{}".format(
                rule._val.name.camel,
                '("{}")'.format(rule.match_text)
                if rule.match_text else ""
            )
    elif isinstance(rule, NoBacktrack):
        return "/"
    elif isinstance(rule, Defer):
        return str(rule)
    elif isinstance(rule, Predicate):
        return "{} |> when({})".format(
            emit_rule(rule.parser), rule.property_name
        )
    elif isinstance(rule, Discard):
        return "discard({})".format(emit_rule(rule.parser))
    else:
        raise NotImplementedError(rule.__class__)


def var_name(var_expr, default="_"):
    return (
        var_expr.source_name.lower if var_expr.source_name else default
    )


def is_simple_expr(expr):
    from langkit.expressions import FieldAccess, Literal, AbstractVariable
    return isinstance(expr, (FieldAccess, Literal, AbstractVariable))


def emit_indent_expr(expr, **ctx):
    strn = emit_expr(expr, **ctx)
    if len(strn) > 40:
        return "$i$hl{}$d$hl".format(strn)
    else:
        return strn


def prepend_comments(expr, **ctx):
    arg_expr = ctx.pop('arg_expr', None)
    if arg_expr is None:
        return emit_expr(expr, **ctx), False

    walker = ctx.get('walker')
    with walker.arg(arg_expr):
        coms = walker.emit_comments()
        strn = emit_expr(expr, **ctx)

    if coms == "":
        return strn, False

    return coms + strn, True


def emit_paren_expr(expr, **ctx):
    from langkit.expressions import Let

    if isinstance(expr, Let):
        return emit_expr(expr, **ctx)

    strn, has_coms = prepend_comments(expr, **ctx)

    if is_simple_expr(expr) and not has_coms:
        return emit_paren(strn) if len(strn) > 40 else strn
    else:
        return emit_paren(strn, force=has_coms)


def emit_paren(strn, force=False):
    if force or len(strn) > 40:
        return "($i$hl{}$d$hl)".format(strn)
    else:
        return "({})".format(strn)


def emit_nl(strn):
    if len(strn) > 40:
        return "$i$hl{}$d$hl".format(strn)
    else:
        return " {} ".format(strn)


def emit_expr(expr, **ctx):
    from langkit.expressions import (
        Literal, Let, FieldAccess, AbstractVariable, SelfVariable,
        EntityVariable, LogicTrue, LogicFalse, unsugar, Map, All, Any,
        GetSymbol, Match, Eq, BinaryBooleanOperator, Then, OrderingTest,
        Quantifier, If, IsNull, Cast, DynamicVariable, IsA, Not, SymbolLiteral,
        No, Cond, New, CollectionSingleton, Concat, EnumLiteral, EnvGet,
        ArrayLiteral, Arithmetic, PropertyError, CharacterLiteral, Block
    )

    then_underscore_var = ctx.get('then_underscore_var')
    overload_coll_name = ctx.get('overload_coll_name')
    walker = ctx.get('walker')

    def is_a(*names):
        return any(expr.__class__.__name__ == n for n in names)

    def emit_lambda(expr, vars):
        vars_str = ", ".join(var_name(var) for var in vars)
        return "({}) => {}".format(vars_str, ee(expr))
        del vars_str

    def emit_method_call(receiver, name, args=[]):
        if not args:
            return "{}.{}".format(receiver, name)
        else:
            return "{}.{}{}".format(
                receiver, name, emit_paren(", ".join(args))
            )

    def ee(expr, **extra_ctx):
        full_ctx = dict(ctx, **extra_ctx)
        return emit_expr(expr, **full_ctx)

    def ee_pexpr(expr, **extra_ctx):
        full_ctx = dict(ctx, **extra_ctx)
        return emit_paren_expr(expr, **full_ctx)

    expr = unsugar(expr)

    if isinstance(expr, Literal):
        return str(expr.literal).lower()
    elif isinstance(expr, SymbolLiteral):
        return '"{}"'.format(expr.name)
    elif isinstance(expr, PropertyError):
        return "raise PropertyError({})".format(
            repr(expr.message) if expr.message else ""
        )
    elif isinstance(expr, IsA):
        return "{} is_a {}".format(
            ee_pexpr(expr.expr),
            ", ".join(type_name(t) for t in expr.astnodes)
        )
    elif isinstance(expr, LogicTrue):
        return "ltrue"
    elif isinstance(expr, LogicFalse):
        return "lfalse"
    elif isinstance(expr, Block):
        if len(expr.vars) == 0:
            with walker.returned_expr():
                coms = walker.emit_comments()
                return ee(expr.expr)

        vars_defs = ""
        for i, (var, abs_expr) in enumerate(zip(expr.vars, expr.var_exprs)):
            with walker.var_assignment(i):
                vars_defs += "{}val {} = {}$hl".format(
                    walker.emit_comments(), var_name(var), ee(abs_expr)
                )
            vars_defs += walker.emit_comments()

        with walker.returned_expr():
            return "{{$i$hl{}$hl{}{}$hl$d}}".format(
                vars_defs, walker.emit_comments(), ee(expr.expr)
            )

    elif isinstance(expr, Let):
        if len(expr.vars) == 0:
            return ee(expr.expr)

        vars_defs = "".join([
            "val {} = {}$hl".format(
                var_name(var), ee(abs_expr)
            ) for var, abs_expr in zip(expr.vars, expr.var_exprs)
        ])

        return "{{$i$hl{}$hl{}$hl$d}}".format(
            vars_defs, ee(expr.expr)
        )
    elif isinstance(expr, Map):
        op_name = expr.kind
        args = []
        vars = [expr.element_var]
        if expr.requires_index:
            vars.append(expr.index_var)
        if op_name in ["map", "mapcat"]:
            args.append(emit_lambda(expr.expr, vars))
        elif op_name == "filter":
            args.append(emit_lambda(expr.filter_expr, vars))
        elif op_name == "filter_map":
            args.append(emit_lambda(expr.expr, vars))
            args.append(emit_lambda(expr.filter_expr, vars))
        elif op_name == "take_while":
            args.append(emit_lambda(expr.take_while_expr, vars))

        if overload_coll_name:
            op_name = overload_coll_name
            del ctx['overload_coll_name']

        coll = ee(expr.collection)

        return emit_method_call(coll, op_name, args)

    elif isinstance(expr, Quantifier):
        return emit_method_call(
            ee(expr.collection),
            expr.kind,
            [emit_lambda(expr.expr, [expr.element_var])]
        )

    elif isinstance(expr, If):
        with walker.call('If'):
            with walker.arg(0):
                coms = walker.emit_comments()
                cond_strn = ee_pexpr(expr.cond)

            res = "{}if {} then {} else {}".format(
                coms,
                cond_strn,
                ee_pexpr(expr._then, arg_expr=1),
                ee_pexpr(expr.else_then, arg_expr=2)
            )
            return res

    elif isinstance(expr, Cond):
        with walker.call('Cond'):
            branches = expr.branches
            res = ""

            for i, b in enumerate(branches):
                # condition
                with walker.arg(i * 2):
                    coms = walker.emit_comments()
                    cond_strn = ee_pexpr(b[0])
                expr_strn = ee_pexpr(b[1], arg_expr=i * 2 + 1)

                res += "{}{} {} then {}$hl".format(
                    coms,
                    "if" if i == 0 else "elif",
                    cond_strn,
                    expr_strn
                )

            with walker.arg(len(branches) * 2):
                coms = walker.emit_comments()
                else_strn = ee_pexpr(expr.else_expr)

            res += "{}else {}".format(coms, else_strn)

            return res

    elif isinstance(expr, IsNull):
        return "{}.is_null".format(ee(expr.expr))

    elif isinstance(expr, Cast):
        return "{}.to{}[{}]".format(
            ee(expr.expr),
            "!" if expr.do_raise else "",
            type_name(expr.dest_type)
        )

    elif isinstance(expr, All):
        return ee(expr.equation_array, overload_coll_name="logic_all")
    elif isinstance(expr, Any):
        return ee(expr.equation_array, overload_coll_name="logic_any")

    elif isinstance(expr, Match):
        with walker.method_call("match"):
            res = ""
            with walker.self_arg():
                coms = walker.emit_comments()
                matched_expr_strn = ee(expr.matched_expr)

            res += "{}match {} {{$i".format(coms, matched_expr_strn)

            for i, (typ, var, e) in enumerate(expr.matchers):
                with walker.arg(i):
                    coms = walker.emit_comments()
                    if coms and i > 0:
                        coms = "$hl" + coms

                    res += "$hl{}case {}{} => {}".format(
                        coms,
                        var_name(var),
                        (" " + sf(": ${type_name(typ)}")) if typ else "",
                        ee(e)
                    )

            res += "$d$hl}"

        return res

    elif isinstance(expr, Eq):
        return "{} == {}".format(ee(expr.lhs), ee(expr.rhs))

    elif isinstance(expr, BinaryBooleanOperator):
        return "{} {} {}".format(
            emit_paren_expr(expr.lhs),
            expr.kind, emit_paren_expr(expr.rhs)
        )

    elif isinstance(expr, Not):
        return "not {}".format(emit_paren_expr(expr.expr))

    elif isinstance(expr, Then):
        if expr.var_expr.source_name is None:
            assert expr.underscore_then
            return "{}?{}".format(
                ee(expr.expr),
                ee(expr.then_expr, then_underscore_var=expr.var_expr)
            )

        res = "{} then {}".format(
            ee_pexpr(expr.expr),
            emit_paren("{} => {}".format(
                var_name(expr.var_expr),
                ee(expr.then_expr),
            )),
        )
        if expr.default_val:
            res += " else {}".format(ee_pexpr(expr.default_val))

        return res

    elif isinstance(expr, OrderingTest):
        return "{} {} {}".format(
            ee_pexpr(expr.lhs),
            expr.OPERATOR_IMAGE[expr.operator],
            ee_pexpr(expr.rhs)
        )

    elif isinstance(expr, GetSymbol):
        return "{}.symbol".format(ee(expr.node_expr))
    elif is_a("as_entity", "as_bare_entity", "at_or_raise", "children",
              "env_parent", "rebindings_parent", "parents", "parent", "root",
              "append_rebinding", "concat_rebindings", "env_node",
              "rebindings_new_env", "rebindings_old_env", "get_value",
              "solve", "is_referenced_from", "env_group", "length"):
        exprs = expr.sub_expressions
        return emit_method_call(ee(exprs[0]), type(expr).__name__,
                                map(ee, exprs[1:]))

    elif isinstance(expr, EnumLiteral):
        return expr.value.dsl_name

    elif isinstance(expr, Arithmetic):
        return "{} {} {}".format(ee_pexpr(expr.l), expr.op, ee_pexpr(expr.r))

    elif isinstance(expr, EnvGet):
        args = [ee(expr.symbol)]
        if expr.sequential_from:
            args.append("from={}".format(ee(expr.sequential_from)))
        if expr.only_first:
            args.append("only_first={}".format(ee(expr.only_first)))
        return emit_method_call(ee(expr.env), "get", args)

    elif is_a("bind"):
        return "bind{}in$i$hl{}$d$hlend".format(
            emit_nl("{}={}".format(ee(expr.expr_0), ee(expr.expr_1))),
            ee(expr.expr_2)
        )
    elif is_a("at"):
        # Recognize find
        if (isinstance(expr.expr_0, Map) and expr.expr_0.kind == 'filter' and
                ee(expr.expr_1) == "0"):
            return ee(expr.expr_0, overload_coll_name="find")

        return "{}?[{}]".format(ee(expr.expr_0), ee(expr.expr_1))
    elif isinstance(expr, FieldAccess):
        args = []
        if expr.arguments:
            for arg in expr.arguments.args:
                args.append(ee(arg))
            for name, arg in expr.arguments.kwargs.items():
                args.append("{}={}".format(name, ee(arg)))

        return emit_method_call(ee(expr.receiver), expr.field, args)

    elif isinstance(expr, Concat):
        return "{} & {}".format(ee_pexpr(expr.array_1), ee_pexpr(expr.array_2))

    elif isinstance(expr, EntityVariable):
        return "entity"
    elif isinstance(expr, SelfVariable):
        return "self"
    elif isinstance(expr, DynamicVariable):
        return expr.argument_name.lower
    elif isinstance(expr, AbstractVariable):
        if then_underscore_var:
            if id(then_underscore_var) == id(expr):
                return ""
        return var_name(expr)
    elif isinstance(expr, No):
        return "null"
    elif isinstance(expr, CollectionSingleton):
        return "[{}]".format(ee(expr.expr))
    elif isinstance(expr, New):
        return "new {}{}".format(
            type_name(expr.struct_type),
            emit_paren(", ".join(
                "{}={}".format(k, ee(v)) for k, v in expr.field_values.items()
            ))
        )
    elif isinstance(expr, ArrayLiteral):
        if isinstance(expr.elements[0], CharacterLiteral):
            return repr(u"".join(e.literal for e in expr.elements))[1:]
        return "[{}]".format(", ".join(ee(el) for el in expr.elements))
    elif isinstance(expr, CharacterLiteral):
        # Get rid of the 'u' unicode prefix
        return repr(expr.literal)[1:]
    else:
        # raise NotImplementedError(type(expr))
        return repr(expr)


def emit_doc(doc):
    from inspect import cleandoc
    doc = cleandoc(doc).replace("\n", "$hl")
    return sf("\"\"\"$hl${doc}$hl\"\"\"")


def emit_prop(prop, walker):
    quals = ""

    if prop.is_public:
        quals += "@export "

    if prop.abstract:
        quals += "abstract "

    if prop.memoized:
        quals += "memoized "

    args = ", ".join("{} : {}{}".format(
        arg.name.lower, type_name(arg.type),
        " = {}".format(emit_expr(arg.abstract_default_value))
        if arg.abstract_default_value else ""
    ) for arg in prop.natural_arguments)

    doc = prop.doc

    res = ""
    if doc:
        res += "$hl{}".format(emit_doc(doc))

    res += "$hl{}fun {} ({}): {}".format(
        quals, prop.original_name.lower, args, type_name(prop.type)
    )

    if prop.expr:
        with walker.property(prop):
            res += " = $sl{}".format(emit_expr(prop.expr, walker=walker))

    return res


def emit_field(field):
    from langkit.compiled_types import BaseField, Field
    if isinstance(field, BaseField):
        return "@{}field {} : {}".format(
            "parse_" if isinstance(field, Field) else "",
            field._indexing_name, type_name(field.type)
        )
    else:
        raise NotImplementedError()


def type_name(type):
    from langkit.compiled_types import ASTNodeType, resolve_type

    type = resolve_type(type)
    if isinstance(type, ASTNodeType):
        if type.is_list_type:
            return "ASTList[{}]".format(type_name(type.element_type))
        else:
            return type.raw_name.camel
    elif type.is_array_type:
        return "Array[{}]".format(type_name(type.element_type))
    elif type.is_entity_type:
        return "Entity[{}]".format(type_name(type.element_type))
    elif type.is_struct_type:
        return type.api_name.camel
    else:
        return type.name.camel


def emit_node_type(node_type):
    if node_type.is_generic_list_type:
        return ""

    walker = DSLWalker.class_from_location(node_type.location)

    base = node_type.base
    parse_fields = node_type.get_fields(
        include_inherited=False
    )
    properties = node_type.get_properties(include_inherited=False)
    enum_qual = (
        "qualifier " if node_type.is_bool_node
        else "enum " if node_type.is_enum_node else ""
    )
    doc = node_type.doc
    builtin_properties = node_type.builtin_properties()

    def is_builtin_prop(prop):
        return any(
            builtin_name == prop.name.lower
            for builtin_name, _ in builtin_properties
        )

    if base and base.is_enum_node:
        return ""

    return sf("""
    % if doc:
    ${emit_doc(doc)}$hl
    % endif
    % if base:
    ${enum_qual}class ${type_name(node_type)} : ${type_name(base)} {$i$hl
    % else:
    ${enum_qual}class ${type_name(node_type)} {$i$hl
    % endif
    % for field in parse_fields:
    ${emit_field(field)}$hl
    % endfor
    % if enum_qual == "enum ":
        case $i${(", $sl".join(alt.name.camel
                               for alt in node_type.alternatives))}$d$hl
    % endif
    % for prop in properties:
    % if not prop.is_internal and not is_builtin_prop(prop):
    ${emit_prop(prop, walker)}$hl
    % endif
    % endfor
    $d
    }$hl
    """.strip())

    del base, parse_fields, enum_qual, properties


def unparse_lang(ctx):
    """
    Unparse the language currently being compiled.
    """

    dest_file = ctx.emitter.unparse_destination_file

    # If there is no destination file, then the pass does nothing.
    if not ctx.emitter.unparse_destination_file:
        return

    # By setting the context's emitter to `None`, we disable the sanity checks
    # done to ensure that we don't intermix codegen and semantic checks in the
    # langkit code generator, because we break that invariant in the unparser.
    emitter = ctx.emitter
    ctx.emitter = None

    template = """
    grammar ${ctx.short_name}_grammar {$i$hl
    % for name, rule in ctx.grammar.rules.items():
        % if not rule.is_dont_skip_parser:
            ${name} <- ${emit_rule(rule)}$hl
        % endif
    % endfor
    $d$hl
    }$hl

    <% types = keep(emit_node_type(t) for t in ctx.astnode_types) %>

    % for t in types:
        $hl
        ${t}
    % endfor
    """

    from time import time
    lang_def = pp(sf(template))
    with open(dest_file, 'w') as f:
        f.write(lang_def)

    ctx.emitter = emitter


def create():
    return GlobalPass('Unparse language definition', unparse_lang)


def pp(strn, indent_step=4, line_size=80):
    from cStringIO import StringIO
    import re
    buf = re.split("(\$hl|\$sl|\$i|\$d)", strn)
    file_str = StringIO()
    indent_level = 0
    current_line = ""

    def write_line():
        file_str.write(current_line.rstrip() + "\n")

    for i in range(len(buf)):
        el = buf[i].replace("\n", "")

        if el in ['$hl', '$sl']:

            len_next_line = 0
            if el == '$sl':
                for j in range(i + 1, len(buf)):
                    if buf[j] == '$hl':
                        break
                    len_next_line += len(buf[j])

            if el == '$hl' or len(current_line) + len_next_line > line_size:
                write_line()
                current_line = " " * indent_level
        elif el == '$i':
            indent_level += indent_step
        elif el == '$d':
            indent_level -= indent_step
            # Reset current line if there is only whitespace on it
            if current_line.strip() == "":
                current_line = " " * indent_level
        else:
            current_line += el
    if current_line:
        write_line()
    return file_str.getvalue()
