from typing import Union, List, Optional

from .exceptions import ParserError, ErrorCode
from .lexer import Location, Token, TokenType, Lexer


class OperatorInfo:
    def __init__(self, token_type: TokenType, precedence: int, associativity: bool):
        self.token_type: TokenType = token_type
        self.value: str = token_type.value
        self.precedence: int = precedence
        self.associativity: bool = associativity  # True 为从左到右，False 为从右到左


assignment_token_list = [
    TokenType.ASSIGN,  # =
    TokenType.PLUS_ASSIGN,  # +=
    TokenType.MINUS_ASSIGN,  # -=
    TokenType.MUL_ASSIGN,  # *=
    TokenType.DIV_ASSIGN,  # /=
    TokenType.MOD_ASSIGN,  # %=
]

literal_const = [
    OperatorInfo(TokenType.NULL, 10, True),  # null 字面量
    OperatorInfo(TokenType.TRUE, 10, True),  # 布尔字面量
    OperatorInfo(TokenType.FALSE, 10, True),  # 布尔字面量
    OperatorInfo(TokenType.INTEGER, 10, True),  # 整数字面量
    OperatorInfo(TokenType.FLOAT, 10, True),  # 浮点数字面量
    OperatorInfo(TokenType.STRING, 10, True),  # 字符串字面量
]

atom_operator_list = literal_const + [
    OperatorInfo(TokenType.ID, 10, True),  # ID
    OperatorInfo(TokenType.FUNC, 10, True),  # func 函数声明语法
    OperatorInfo(TokenType.VBAR, 10, True),
    OperatorInfo(TokenType.LBRACE, 10, True),  # { table 构造语法
]

# 此类运算符仅能跟在原子之后
primary_operator_list = [
    OperatorInfo(TokenType.LPAREN, 9, True),  # ( 函数调用语法
    OperatorInfo(TokenType.LBRACKET, 9, True),  # [ 成员引用语法
    OperatorInfo(TokenType.POINT, 9, True),  # . 成员引用语法
    OperatorInfo(TokenType.DOUBLE_COLON, 9, True),  # :: 成员引用语法
]

unary_operator_list = [
    OperatorInfo(TokenType.ADD, 8, False),  # +
    OperatorInfo(TokenType.SUB, 8, False),  # -
    OperatorInfo(TokenType.NOT, 8, False),  # not
    OperatorInfo(TokenType.HASH, 8, False),  # #
]

binary_operator_list = [
    OperatorInfo(TokenType.MUL, 7, True),  # *
    OperatorInfo(TokenType.DIV, 7, True),  # /
    OperatorInfo(TokenType.MOD, 7, True),  # %

    OperatorInfo(TokenType.ADD, 6, True),  # +
    OperatorInfo(TokenType.SUB, 6, True),  # -

    OperatorInfo(TokenType.LESS, 5, True),  # <
    OperatorInfo(TokenType.LESS_EQUAL, 5, True),  # <=
    OperatorInfo(TokenType.GREATER, 5, True),  # >
    OperatorInfo(TokenType.GREATER_EQUAL, 5, True),  # >=

    OperatorInfo(TokenType.EQUAL, 4, True),  # ==
    OperatorInfo(TokenType.NOT_EQUAL, 4, True),  # !=

    OperatorInfo(TokenType.IS, 3, True),  # is

    OperatorInfo(TokenType.AND, 2, True),  # and
    OperatorInfo(TokenType.OR, 1, True),  # or
]


def get_operator_token_type_list(operator_list: List[OperatorInfo]):
    return map(lambda x: x.token_type, operator_list)


class ASTNode:
    def __init__(self, start: Location = None, end: Location = None):
        self.start: Location = start
        self.end: Location = end


class Statement(ASTNode):
    pass


class Expression(ASTNode):
    pass


class Literal(Expression):
    def __init__(self, value: Union[None, bool, str, int, float] = None,
                 start: Location = None, end: Location = None):
        super().__init__(start=start, end=end)
        self.value: Union[None, bool, str, int, float] = value

    def __repr__(self):
        return repr(self.value)


class Identifier(Expression):
    def __init__(self, name: str = None,
                 start: Location = None, end: Location = None):
        super().__init__(start=start, end=end)
        self.name: str = name

    def __repr__(self):
        return self.name


class Property(ASTNode):
    def __init__(self, key: Union[Identifier, Literal] = None, value: Expression = None,
                 start: Location = None, end: Location = None):
        super().__init__(start=start, end=end)
        self.key: Union[Identifier, Literal] = key
        self.value: Expression = value

    def __repr__(self):
        return f'{self.key!r}: {self.value!r}'


class ImportNameAlias(ASTNode):
    def __init__(self, name: Identifier = None, alias: Optional[Identifier] = None,
                 start: Location = None, end: Location = None):
        super().__init__(start=start, end=end)
        self.name: Identifier = name
        self.alias: Optional[Identifier] = alias

    def __repr__(self):
        return self.name.name + ((' as ' + self.alias.name) if self.alias is not None else '')


class BlockStatement(Statement):
    def __init__(self, body: List[Statement] = None,
                 start: Location = None, end: Location = None):
        super().__init__(start=start, end=end)
        if body is None:
            body = list()
        self.body: List[Statement] = body

    def __repr__(self):
        return '{' + ''.join(map(lambda x: repr(x) + ';', self.body)) + '}'


class IfStatement(Statement):
    def __init__(self, test: Expression = None, consequent: Statement = None, alternate: Statement = None,
                 start: Location = None, end: Location = None):
        super().__init__(start=start, end=end)
        self.test: Expression = test
        self.consequent: Statement = consequent
        self.alternate: Statement = alternate

    def __repr__(self):
        return f'if({self.test!r}){self.consequent!r}' + (repr(self.alternate) if self.alternate is not None else '')


class LoopStatement(Statement):
    def __init__(self, body: Statement = None,
                 start: Location = None, end: Location = None):
        super().__init__(start=start, end=end)
        self.body: Statement = body

    def __repr__(self):
        return f'loop{self.body!r}'


class WhileStatement(LoopStatement):
    def __init__(self, test: Expression = None, body: Statement = None,
                 start: Location = None, end: Location = None):
        super().__init__(body=body, start=start, end=end)
        self.test: Expression = test

    def __repr__(self):
        return f'while({self.test!r}){self.body!r}'


class ForStatement(Statement):
    def __init__(self, left: Identifier = None, right: Expression = None, body: Statement = None,
                 start: Location = None, end: Location = None):
        super().__init__(start=start, end=end)
        self.left: Identifier = left
        self.right: Expression = right
        self.body: Statement = body

    def __repr__(self):
        return f'for({self.left!r} in {self.right!r}){self.body}'


class BreakStatement(Statement):
    def __repr__(self):
        return 'break;'


class ContinueStatement(Statement):
    def __repr__(self):
        return 'continue;'


class GotoStatement(Statement):
    def __init__(self, argument: 'CallExpression' = None,
                 start: Location = None, end: Location = None):
        super().__init__(start=start, end=end)
        self.argument: 'CallExpression' = argument

    def __repr__(self):
        return f'goto {self.argument!r};'


class ReturnStatement(Statement):
    def __init__(self, argument: Expression = None,
                 start: Location = None, end: Location = None):
        super().__init__(start=start, end=end)
        self.argument: Optional[Expression] = argument

    def __repr__(self):
        return f'return {self.argument!r};'


class GlobalStatement(Statement):
    def __init__(self, arguments: List[Identifier] = None,
                 start: Location = None, end: Location = None):
        super().__init__(start=start, end=end)
        if arguments is None:
            arguments = list()
        self.arguments: List[Identifier] = arguments

    def __repr__(self):
        return f'global {", ".join(map(lambda x: repr(x), self.arguments))};'


class AssignmentStatement(Statement):
    def __init__(self, left: Union[Identifier, 'MemberExpression'] = None, operator: str = None,
                 right: Expression = None,
                 start: Location = None, end: Location = None):
        super().__init__(start=start, end=end)
        self.left: Union[Identifier, 'MemberExpression'] = left
        self.operator: str = operator
        self.right: Expression = right

    def __repr__(self):
        return f'({self.left!r} {self.operator} {self.right!r})'


class ImportStatement(Statement):
    def __init__(self, paths: List[Identifier] = None, names: List[ImportNameAlias] = None, star: bool = False,
                 start: Location = None, end: Location = None):
        super().__init__(start=start, end=end)
        if paths is None:
            paths = list()
        if names is None:
            names = list()
        self.paths: List[Identifier] = paths
        self.names: List[ImportNameAlias] = names
        self.star: bool = star

    def __repr__(self):
        if self.star:
            return f'import {"::".join(map(lambda x: x.name, self.paths))}::*;'
        elif len(self.paths) == 0:
            return f'import {self.names[0]!r};'
        else:
            return 'import ' + '::'.join(map(lambda x: x.name, self.paths)) + \
                   '::{' + ', '.join(map(repr, self.names)) + '};'


class FunctionExpression(Expression):
    def __init__(self, params: List[Identifier] = None, body: BlockStatement = None, is_closure: bool = False,
                 start: Location = None, end: Location = None):
        super().__init__(start=start, end=end)
        if params is None:
            params = list()

        self.params: List[Identifier] = params
        self.body: BlockStatement = body
        self.is_closure: bool = is_closure

    def __repr__(self):
        if self.is_closure:
            return f'|{", ".join(map(lambda x: repr(x), self.params))}|{self.body!r}'
        return f'func({", ".join(map(lambda x: repr(x), self.params))}){self.body!r}'


class TableExpression(Expression):
    def __init__(self, properties: List[Property] = None,
                 start: Location = None, end: Location = None):
        super().__init__(start=start, end=end)
        if properties is None:
            properties = list()
        self.properties: List[Property] = properties

    def __repr__(self):
        return '{' + ', '.join(map(lambda x: f'{x.key!r}: {x.value!r}', self.properties)) + '}'


class UnaryExpression(Expression):
    def __init__(self, operator: str = None, prefix: bool = None, argument: Expression = None,
                 start: Location = None, end: Location = None):
        super().__init__(start=start, end=end)
        self.operator: str = operator
        self.prefix: bool = prefix
        self.argument: Expression = argument

    def __repr__(self):
        return f'({self.operator}{self.argument!r})'


class BinaryExpression(Expression):
    def __init__(self, left: Expression = None, operator: str = None, right: Expression = None,
                 start: Location = None, end: Location = None):
        super().__init__(start=start, end=end)
        self.left: Expression = left
        self.operator: str = operator
        self.right: Expression = right

    def __repr__(self):
        return f'({self.left!r} {self.operator} {self.right!r})'


class MemberExpression(Expression):
    def __init__(self, table: Expression = None, property: Expression = None, expression_type: str = None,  # noqa
                 start: Location = None, end: Location = None):
        super().__init__(start=start, end=end)
        self.table: Expression = table
        self.property: Expression = property
        self.expression_type: str = expression_type
        # computed 为 True 时表示是由 [] 语法产生的，需要对 property 进行计算
        # computed 为 False 时表示是由 . 语法生成的，property 一定是 Identifier，解释为字符串字面量

    def __repr__(self):
        if self.expression_type == '[]':
            return f'({self.table!r}[{self.property!r}])'
        else:
            return f'({self.table!r}{self.expression_type}{self.property!r})'


class CallExpression(Expression):
    def __init__(self, callee: Expression = None, arguments: List[Expression] = None,
                 start: Location = None, end: Location = None):
        super().__init__(start=start, end=end)
        self.callee: Expression = callee
        if arguments is None:
            arguments = list()
        self.arguments: List[Expression] = arguments

    def __repr__(self):
        return f'{self.callee!r}({", ".join(map(lambda x: repr(x), self.arguments))})'


class Program(BlockStatement):
    def __init__(self):
        super().__init__(start=None, end=None)


class Parser:
    def __init__(self, lexer: Lexer):
        self.lexer: Lexer = lexer
        self.previous_token: Optional[Token] = None
        self.current_token: Token = self.lexer.get_next_token()
        self.ast: Program = Program()

    def error(self,
              error_code: ErrorCode = ErrorCode.UNEXPECTED_TOKEN,
              token: Token = None,
              expect_token_type: TokenType = None):
        if token is None:
            token = self.current_token
        if expect_token_type is None:
            message = repr(token)
        else:
            message = f'Expect {expect_token_type.value}, but {token!r} was given'
        raise ParserError(error_code=error_code, message=message)

    def advance_token(self):
        if self.current_token.type == TokenType.EOF:
            raise ParserError(error_code=ErrorCode.UNEXPECTED_TOKEN,
                              message=f'Unexpect end of file {self.current_token}')
        self.previous_token = self.current_token
        self.current_token = self.lexer.get_next_token()

    def advance_token_match(self, token_type: TokenType):
        self.advance_token()
        self.token_match(token_type)

    def token_match(self, token_type: TokenType):
        if self.current_token.type != token_type:
            self.error(expect_token_type=token_type)

    def parse(self):
        while self.current_token.type != TokenType.EOF:
            self.ast.body.append(self.parse_statement())
        return self.ast

    def parse_statement(self):
        ast_node = None
        if self.current_token.type == TokenType.IF:
            # if
            ast_node = IfStatement()
            ast_node.start = self.current_token.start
            self.advance_token()
            ast_node.test = self.parse_expression()
            ast_node.consequent = self.parse_statement_block()
            if self.current_token.type == TokenType.ELSE:
                self.advance_token()
                ast_node.alternate = self.parse_statement_block()
            ast_node.end = self.previous_token.end
        elif self.current_token.type == TokenType.ELSE:
            # else
            self.error()
        elif self.current_token.type == TokenType.LOOP:
            # loop
            ast_node = LoopStatement()
            ast_node.start = self.current_token.start
            self.advance_token()
            ast_node.body = self.parse_statement_block()
            ast_node.end = self.previous_token.end
        elif self.current_token.type == TokenType.WHILE:
            # while
            ast_node = WhileStatement()
            ast_node.start = self.current_token.start
            self.advance_token()
            ast_node.test = self.parse_expression()
            ast_node.body = self.parse_statement_block()
            ast_node.end = self.previous_token.end
        elif self.current_token.type == TokenType.FOR:
            # for
            ast_node = ForStatement()
            ast_node.start = self.current_token.start
            self.advance_token()
            ast_node.left = self.parse_expression_identifier()
            self.advance_token_match(TokenType.IN)
            self.advance_token()
            ast_node.right = self.parse_expression()
            ast_node.body = self.parse_statement_block()
            ast_node.end = self.previous_token.end
        elif self.current_token.type == TokenType.IN:
            # in
            self.error()
        elif self.current_token.type == TokenType.BREAK:
            # break
            ast_node = BreakStatement()
            ast_node.start = self.current_token.start
            self.advance_token_match(TokenType.SEMI)
            self.advance_token()
            ast_node.end = self.previous_token.end
        elif self.current_token.type == TokenType.CONTINUE:
            # continue
            ast_node = ContinueStatement()
            ast_node.start = self.current_token.start
            self.advance_token_match(TokenType.SEMI)
            self.advance_token()
            ast_node.end = self.previous_token.end
        elif self.current_token.type == TokenType.GOTO:
            # goto
            ast_node = GotoStatement()
            ast_node.start = self.current_token.start
            self.advance_token()
            ast_node.argument = self.parse_expression()
            if not isinstance(ast_node.argument, CallExpression):
                raise ParserError(
                    error_code=ErrorCode.GOTO_UNEXPECTED_EXPRESSION,
                    message=f'Goto statement must with call expression, but {ast_node.argument} was given'
                )
            self.token_match(TokenType.SEMI)
            self.advance_token()
            ast_node.end = self.previous_token.end
        elif self.current_token.type == TokenType.RETURN:
            # return
            ast_node = ReturnStatement()
            ast_node.start = self.current_token.start
            self.advance_token()
            ast_node.argument = self.parse_expression()
            self.token_match(TokenType.SEMI)
            self.advance_token()
            ast_node.end = self.previous_token.end
        elif self.current_token.type == TokenType.GLOBAL:
            # global
            ast_node = GlobalStatement()
            ast_node.start = self.current_token.start
            while self.current_token.type != TokenType.SEMI:
                self.advance_token()
                ast_node.arguments.append(self.parse_expression_identifier())
                self.advance_token()
                if self.current_token.type != TokenType.SEMI and self.current_token.type != TokenType.COMMA:
                    self.error(expect_token_type=TokenType.COMMA)
            self.advance_token()
            ast_node.end = self.previous_token.end
        elif self.current_token.type == TokenType.IMPORT:
            ast_node = ImportStatement()
            ast_node.start = self.current_token.start
            self.advance_token()
            while self.current_token.type not in [TokenType.SEMI, TokenType.AS, TokenType.LBRACE]:
                if self.current_token.type == TokenType.MUL:
                    ast_node.star = True
                    self.advance_token_match(TokenType.SEMI)
                    break
                else:
                    self.token_match(TokenType.ID)
                    ast_node.paths.append(self.parse_expression_identifier())
                    self.advance_token()
                    if self.current_token.type in [TokenType.SEMI, TokenType.AS, TokenType.LBRACE]:
                        break
                    self.token_match(TokenType.DOUBLE_COLON)
                    self.advance_token()
            if self.current_token.type == TokenType.SEMI:
                if not ast_node.star:
                    temp = ast_node.paths.pop()
                    ast_node.names.append(ImportNameAlias(name=temp, start=temp.start, end=temp.end))
            elif self.current_token.type == TokenType.AS:
                self.advance_token_match(TokenType.ID)
                temp = ast_node.paths.pop()
                ast_node.names.append(ImportNameAlias(name=temp, alias=self.parse_expression_identifier(),
                                                      start=temp.start, end=temp.end))
                self.advance_token_match(TokenType.SEMI)
            elif self.current_token.type == TokenType.LBRACE:
                self.advance_token_match(TokenType.ID)
                while self.current_token.type != TokenType.RBRACE:
                    self.token_match(TokenType.ID)
                    temp = ImportNameAlias(name=self.parse_expression_identifier())
                    temp.start = self.current_token.start
                    ast_node.names.append(temp)
                    self.advance_token()
                    if self.current_token.type == TokenType.AS:
                        self.advance_token_match(TokenType.ID)
                        temp.alias = self.parse_expression_identifier()
                        temp.end = self.current_token.end
                        self.advance_token()
                    if self.current_token.type == TokenType.RBRACE:
                        temp.end = self.previous_token.end
                        break
                    self.token_match(TokenType.COMMA)
                    self.advance_token()
                self.advance_token_match(TokenType.SEMI)
            self.advance_token()
            ast_node.end = self.previous_token.end
        elif self.current_token.type == TokenType.LBRACE:
            # block
            return self.parse_statement_block()
        else:
            # func 不需要单独解析，通过 parse_expression 解析
            ast_node = self.parse_expression()
            if self.current_token.type in assignment_token_list:
                assignment_token = self.current_token.type
                if not isinstance(ast_node, Identifier) and not isinstance(ast_node, MemberExpression):
                    raise ParserError(error_code=ErrorCode.ASSIGNING_TO_RVALUE,
                                      message=f'Can only assigning to id or member expression, not {ast_node!r}')
                self.advance_token()
                right = self.parse_expression()
                ast_node = AssignmentStatement(ast_node, assignment_token.value, right,
                                               start=ast_node.start, end=right.end)
            self.token_match(TokenType.SEMI)
            self.advance_token()
        return ast_node

    def parse_statement_block(self):
        self.token_match(TokenType.LBRACE)
        ast_node = BlockStatement()
        ast_node.start = self.current_token.start
        self.advance_token()
        while self.current_token.type != TokenType.RBRACE:
            ast_node.body.append(self.parse_statement())
        self.advance_token()
        ast_node.end = self.previous_token.end
        return ast_node

    def parse_expression(self, min_precedence: int = 1):
        start = self.current_token.start
        left = self.parse_expression_unary()
        while True:
            current_operator_info = None
            for operator_info in binary_operator_list:
                if operator_info.token_type == self.current_token.type:
                    current_operator_info = operator_info
            if current_operator_info is None or current_operator_info.precedence < min_precedence:
                break
            precedence = current_operator_info.precedence
            self.advance_token()
            right = self.parse_expression(precedence + 1 if current_operator_info.associativity else precedence)
            left = BinaryExpression(left, current_operator_info.value, right, start=start, end=self.previous_token.end)
        return left

    def parse_expression_unary(self):
        if self.current_token.type in get_operator_token_type_list(atom_operator_list) or \
                self.current_token.type == TokenType.LPAREN:
            # 处理原子，括号表达式视为原子
            return self.parse_expression_primary()
        elif self.current_token.type in get_operator_token_type_list(unary_operator_list):
            # 处理一元运算符
            start = self.current_token.start
            operator = self.current_token.value
            self.advance_token()
            return UnaryExpression(operator, True, self.parse_expression_primary(),
                                   start=start, end=self.previous_token.end)
        elif self.current_token.type in get_operator_token_type_list(binary_operator_list):
            self.error()
        return None

    def parse_expression_primary(self):
        start = self.current_token.start
        ast_node = self.parse_expression_atom()
        while self.current_token.type in get_operator_token_type_list(primary_operator_list):
            if self.current_token.type == TokenType.LPAREN:
                # 函数调用 ()
                ast_node = CallExpression(callee=ast_node,
                                          start=start)
                self.advance_token()
                while self.current_token.type != TokenType.RPAREN:
                    ast_node.arguments.append(self.parse_expression())
                    if self.current_token.type == TokenType.RPAREN:
                        break
                    self.token_match(TokenType.COMMA)
                    self.advance_token()
                ast_node.end = self.current_token.end
                self.advance_token()
            elif self.current_token.type == TokenType.LBRACKET:
                # 成员引用 []
                ast_node = MemberExpression(table=ast_node, expression_type='[]',
                                            start=start)
                self.advance_token()
                ast_node.property = self.parse_expression()
                self.token_match(TokenType.RBRACKET)
                ast_node.end = self.current_token.end
                self.advance_token()
            elif self.current_token.type == TokenType.POINT or self.current_token.type == TokenType.DOUBLE_COLON:
                # 成员引用 . 和 ::
                ast_node = MemberExpression(table=ast_node, expression_type=self.current_token.type.value,
                                            start=start)
                self.advance_token()
                ast_node.property = self.parse_expression_identifier()
                ast_node.end = self.current_token.end
                self.advance_token()
        return ast_node

    def parse_expression_atom(self):
        ast_node = None
        if self.current_token.type == TokenType.LPAREN:
            # 括号，表示优先级提高
            self.advance_token()
            ast_node = self.parse_expression()
            self.token_match(TokenType.RPAREN)
            self.advance_token()
        elif self.current_token.type == TokenType.FUNC or self.current_token.type == TokenType.VBAR:
            # 函数声明语法
            ast_node = self.parse_expression_func()
        elif self.current_token.type == TokenType.LBRACE:
            # table 声明语法
            ast_node = self.parse_expression_table()
        elif self.current_token.type == TokenType.ID:
            # id
            ast_node = self.parse_expression_identifier()
            self.advance_token()
        elif self.current_token.type in get_operator_token_type_list(literal_const):
            # 字面量
            ast_node = Literal(self.current_token.value,
                               start=self.current_token.start, end=self.current_token.end)
            self.advance_token()
        else:
            self.error()
        return ast_node

    def parse_expression_identifier(self):
        self.token_match(TokenType.ID)
        return Identifier(self.current_token.value,
                          start=self.current_token.start, end=self.current_token.end)

    def parse_expression_func(self):
        ast_node = FunctionExpression()
        ast_node.start = self.current_token.start
        if self.current_token.type == TokenType.FUNC:
            # func(...){}
            self.advance_token_match(TokenType.LPAREN)
            end_token = TokenType.RPAREN
            ast_node.is_closure = False
        else:
            # |...|{}
            end_token = TokenType.VBAR
            ast_node.is_closure = True
        self.advance_token()
        while self.current_token.type != end_token:
            ast_node.params.append(self.parse_expression_identifier())
            self.advance_token()
            if self.current_token.type == end_token:
                break
            self.token_match(TokenType.COMMA)
            self.advance_token()
        self.advance_token()
        ast_node.body = self.parse_statement_block()
        ast_node.end = self.previous_token.end
        return ast_node

    def parse_expression_table(self):
        ast_node = TableExpression()
        ast_node.start = self.current_token.start
        count = 0
        self.advance_token()
        while self.current_token.type != TokenType.RBRACE:
            property_node = Property()
            property_node.start = self.current_token.start
            temp_expression = self.parse_expression()
            if self.current_token.type == TokenType.COLON:
                property_node.key = temp_expression
                self.advance_token()
                property_node.value = self.parse_expression()
            else:
                property_node.key = Literal(count, start=property_node.start, end=property_node.start)
                property_node.value = temp_expression
            count += 1
            property_node.end = self.previous_token.end
            ast_node.properties.append(property_node)
            if self.current_token.type == TokenType.RBRACE:
                break
            self.token_match(TokenType.COMMA)
            self.advance_token()
        self.advance_token()
        ast_node.end = self.previous_token.end
        return ast_node
