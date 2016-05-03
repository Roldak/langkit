from langkit.compiled_types import LogicVarType, EquationType
from langkit.expressions.base import (
    AbstractExpression, construct, ResolvedExpression, PropertyDef
)
from langkit.expressions.envs import Env


class Bind(AbstractExpression):
    """
    This expression binds two logic variables A and B, through a property call,
    so that, in logical terms::

        B = A.property_call()

    Which is expressed in the DSL as::

        Bind(A, B, property)
    """

    class Expr(ResolvedExpression):
        def __init__(self, from_var, to_var, bind_property):
            self.from_var = from_var
            ":type: ResolvedExpression"

            self.to_var = to_var
            ":type: ResolvedExpression"

            self.bind_property = bind_property
            ":type: PropertyDef"

        @property
        def type(self):
            return EquationType

        def render_pre(self):
            return "\n".join([self.from_var.render_pre(),
                              self.to_var.render_pre()])

        def render_expr(self):
            return ("{t}_{p}_Bind.Create "
                    "({l}, {r}, {t}_{p}_Logic_Binder'(Env => {e}))").format(
                t=self.bind_property.ast_node.name(),
                p=self.bind_property.name,
                l=self.from_var.render_expr(),
                r=self.to_var.render_expr(),
                e=Env.construct().render_expr(),
            )

    def __init__(self, from_var, to_var, bind_property):
        """
        :param AbstractExpression from_var: An expression resolving to a
            logical variable that is the source of the bind.
        :param AbstractExpression to_var: An expression resolving to a
            logical variable that is the destination of the bind.
        :param PropertyDef bind_property: The property to apply on the value of
            from_var that will yield the value to give to to_var.
        """
        super(Bind, self).__init__()
        self.from_var = from_var
        self.to_var = to_var
        self.bind_property = bind_property

    def do_prepare(self):
        self.bind_property.do_generate_logic_binder()

    def construct(self):
        return Bind.Expr(
            construct(self.from_var, LogicVarType),
            construct(self.to_var, LogicVarType),
            self.bind_property
        )


class Domain(AbstractExpression):
    """
    Define the domain of a logical variable. Several important properties about
    this expression:

    This is the entry point into the logic DSL. A variable of LogicVarType
    *must* have a domain defined in the context of an equation. If it doesn't,
    its solution set is empty, and thus the only possible value for it is
    undefined.

    If an equation is defined in which the only constraint on variables is
    their domains, then, for a set A, B, .., N of logical variables, with
    domains DA, DB, .., DN, the set of solutions will be of the product of the
    set of every domains.

    So for example, in the equation::
        Domain(A, [1, 2]) and Domain(B, [1, 2])

    The set of solutions is::
        [(1, 1), (1, 2), (2, 1), (2, 2)]

    The 'or' operator acts like concatenation on domains of logic variable, so
    for example::

        Domain(A, [1, 2]) or Domain(A, [3, 4])

    is equivalent to (but slower than) Domain(A, [1, 2, 3, 4]).

    You can define an equation that is invalid, in that not every equation has
    a domain, and, due to runtime dispatch , we cannot statically predict if
    that's gonna happen. Thus, trying to solve such an equation will result in
    an error.

    Please note that for the moment equations can exist only on AST nodes,
    so the above examples are invalid, and just meant to illustrate the
    semantics.
    """

    class Expr(ResolvedExpression):

        def __init__(self, domain, logic_var_expr):
            self.domain = domain
            self.logic_var_expr = logic_var_expr
            self.res_var = PropertyDef.get().vars.create("Var", EquationType)

        @property
        def type(self):
            return EquationType

        def render_pre(self):
            return "\n".join([
                self.domain.render_pre(),
                self.logic_var_expr.render_pre(), """
                declare
                    A : Eq_Node.Raw_Member_Array (1 .. Length ({domain}));
                begin
                    for J in 0 .. Length ({domain}) loop
                        A (J) := Get ({domain}, J);
                    end loop;

                    {res_var} := Member ({logic_var}, A);
                end;
                """.format(logic_var=self.logic_var_expr.render_expr(),
                           domain=self.domain.render_expr(),
                           res_var=self.res_var.name)
            ])

        def render_expr(self):
            return str(self.res_var.name)

    def __init__(self, logic_var_expr, domain):
        """
        :param AbstractExpression logic_var_expr: An expression
            that must resolve to an instance of a logic variable.
        :param AbstractExpression domain: An expression that must resolve to
            the domain, which needs to be a collection of a type that
            derives from the root grammar class, or the root grammar class
            itself.
        """
        super(Domain, self).__init__()

        self.domain = domain
        ":type: AbstractExpression"

        self.logic_var_expr = logic_var_expr
        ":type: AbstractExpression"

    def construct(self):
        return Domain.Expr(
            construct(self.domain, lambda d: d.is_collection(), "Type given "
                      "to LogicVar must be collection type, got {expr_type}"),
            construct(self.logic_var_expr, LogicVarType)
        )
