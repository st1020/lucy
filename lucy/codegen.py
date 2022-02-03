from enum import Enum

from .parser import *
from .exceptions import CodeGeneratorError, ErrorCode


class Address:
    address: int = None

    def __repr__(self):
        return f'address({self.address!r})'


class Function(Address):
    def __init__(self, params_num: int, address: int = None):
        self.params_num: int = params_num
        self.address = address
        self.code_list: List[Union[Code, Address]] = list()

    def __repr__(self):
        return f'function({self.address!r})'


T_LITERAL = Union[None, bool, int, float, str, Function]


class ArgumentType(Enum):
    NONE = None
    VARIABLE = str
    NUMBER = int


class OPCode:
    def __init__(self, name: str, argument_num: int, argument_type: ArgumentType):
        self.name: str = name
        self.argument_num: int = argument_num
        self.argument_type: ArgumentType = argument_type

    def __repr__(self):
        return self.name


class OPCodes(Enum):
    PUSH = OPCode('push', 1, ArgumentType.VARIABLE)  # push(A)
    PUSH_LITERAL = OPCode('pushl', 1, ArgumentType.NUMBER)  # push(literal[A])
    TOP = OPCode('top', 1, ArgumentType.VARIABLE)  # A = top
    POP = OPCode('pop', 0, ArgumentType.NONE)  # pop
    GLO = OPCode('glo', 1, ArgumentType.VARIABLE)  # A = &global(A)

    NEW_TABLE = OPCode('new', 0, ArgumentType.NONE)  # push({})
    GET_TABLE_TOP = OPCode('get', 0, ArgumentType.NONE)  # push(top[pop])
    SET_TABLE_TOP = OPCode('set', 0, ArgumentType.NONE)  # top[pop] := pop
    FOR = OPCode('for', 0, ArgumentType.NONE)  # 准备for循环，temp = pop:table，push(0:point)，push(temp)
    FOR_PRE = OPCode('forp', 0, ArgumentType.NONE)  # push(top:table 的当前指针指向的 key) 并且指针前进一格

    NEG = OPCode('neg', 0, ArgumentType.NONE)  # push(-pop)
    NOT = OPCode('not', 0, ArgumentType.NONE)  # push(!pop)

    ADD = OPCode('add', 0, ArgumentType.NONE)  # push(pop + pop)
    SUB = OPCode('sub', 0, ArgumentType.NONE)  # push(pop - pop)
    MUL = OPCode('mul', 0, ArgumentType.NONE)  # push(pop * pop)
    DIV = OPCode('div', 0, ArgumentType.NONE)  # push(pop / pop)
    MOD = OPCode('mod', 0, ArgumentType.NONE)  # push(pop % pop)
    AND = OPCode('and', 0, ArgumentType.NONE)  # push(pop && pop)
    OR = OPCode('or', 0, ArgumentType.NONE)  # push(pop || pop)
    EQ = OPCode('eq', 0, ArgumentType.NONE)  # push(pop == pop)
    NE = OPCode('ne', 0, ArgumentType.NONE)  # push(pop != pop)
    LT = OPCode('lt', 0, ArgumentType.NONE)  # push(pop <  pop)
    LE = OPCode('le', 0, ArgumentType.NONE)  # push(pop <= pop)
    GT = OPCode('gt', 0, ArgumentType.NONE)  # push(pop >  pop)
    GE = OPCode('ge', 0, ArgumentType.NONE)  # push(pop >= pop)

    JMP = OPCode('jmp', 1, ArgumentType.NUMBER)  # PC := $A
    JT = OPCode('jt', 1, ArgumentType.NUMBER)  # if (pop == true) PC := $A
    JF = OPCode('jf', 1, ArgumentType.NUMBER)  # if (pop == false) PC := $A
    JN = OPCode('jn', 1, ArgumentType.NUMBER)  # if (top == null) PC := $A

    # call 和 goto 第一步都是创建新的栈帧，并且依次从当前栈中 pop $A 个参数 push 进新的栈
    CALL = OPCode('call', 1, ArgumentType.NUMBER)  # call 调用新的函数，设置新的栈帧返回地址为自身下一条语句，进入新的栈帧 jmp pop
    GOTO = OPCode('goto', 1, ArgumentType.NUMBER)  # goto 调用新的函数，设置新的栈帧返回地址为当前的返回地址，进入新的栈帧 jmp pop，并销毁当前栈帧
    RET = OPCode('ret', 0, ArgumentType.NONE)  # return 返回并销毁当前栈帧，返回值为 pop
    EXIT = OPCode('exit', 0, ArgumentType.NONE)  # exit 退出

    def __repr__(self):
        return repr(self.value)


binary_operator_to_opcodes = {
    '*': OPCodes.MUL,
    '/': OPCodes.DIV,
    '+': OPCodes.ADD,
    '%': OPCodes.MOD,
    '-': OPCodes.SUB,
    '<': OPCodes.LT,
    '<=': OPCodes.LE,
    '>': OPCodes.GT,
    '>=': OPCodes.GE,
    '==': OPCodes.EQ,
    '!=': OPCodes.NE,
    '&&': OPCodes.AND,
    '||': OPCodes.OR,
}


class Code:
    def __init__(self, opcode: OPCodes, argument: Union[None, int, str, Address] = None):
        self.opcode: OPCodes = opcode
        self.argument: Union[None, int, str, Address] = argument

    def __repr__(self):
        if self.argument is None:
            return repr(self.opcode)
        else:
            return f'{self.opcode!r} {self.argument!r}'


class CodeProgram:
    def __init__(self, code_list: List[Code], literal_list: List[T_LITERAL]):
        self.code_list: List[Code] = code_list
        self.literal_list: List[T_LITERAL] = literal_list


class CodeGenerator:
    def __init__(self, ast: Program):
        self.ast: Program = ast
        self.code_list: List[Union[Code, Address]] = list()
        self.func_list: List[Function] = list()

        self.continue_label_list: List[Address] = list()
        self.break_label_list: List[Address] = list()
        self.literal_list: List[T_LITERAL] = [None, True, False]

    def generate(self):
        self.code_list += self.gen_code(self.ast)
        self.code_list.append(Code(OPCodes.EXIT))
        # 合并 code_list 和 func_list
        for func_code in self.func_list:
            self.code_list += func_code.code_list
        # 地址重定位
        index = 0
        while index < len(self.code_list):
            if isinstance(self.code_list[index], Address):
                self.code_list[index].address = index
                self.code_list.pop(index)
            else:
                index += 1
        for code in self.code_list:
            if isinstance(code.argument, Address):
                code.argument = code.argument.address
        return CodeProgram(self.code_list, self.literal_list)

    def add_literal_list(self, value: T_LITERAL):
        for index, literal_item in enumerate(self.literal_list):
            if type(value) == type(literal_item) and value == literal_item:
                # 在 Python 中 bool 是 int 的子类，故需要判断类型严格相等
                return index
        self.literal_list.append(value)
        return len(self.literal_list) - 1

    def gen_code_statement(self, ast_node: ASTNode):
        code_list = list()
        code_list += self.gen_code(ast_node)
        if isinstance(ast_node, Expression):
            code_list.append(Code(OPCodes.POP))
        return code_list

    def gen_code(self, ast_node: ASTNode):
        code_list = list()
        if isinstance(ast_node, Literal):
            # Literal
            code_list.append(Code(OPCodes.PUSH_LITERAL, self.add_literal_list(ast_node.value)))
        elif isinstance(ast_node, Identifier):
            # Identifier
            code_list.append(Code(OPCodes.PUSH, ast_node.name))
        elif isinstance(ast_node, Property):
            # Property
            raise CodeGeneratorError(ErrorCode.UNEXPECTED_AST_NODE)
        elif isinstance(ast_node, BlockStatement):
            # {}
            for statement in ast_node.body:
                code_list += self.gen_code_statement(statement)
        elif isinstance(ast_node, IfStatement):
            # if
            # if (...) <statement> [else <statement>]
            #
            #   if (<cond>)                   <cond>
            #                                 JZ a
            #     <true_statement>   ===>     <true_statement>
            #   else:                         JMP b
            # a:                           a:
            #     <false_statement>           <false_statement>
            # b:                           b:
            false_label = Address()
            if ast_node.alternate is None:
                end_label = false_label
            else:
                end_label = Address()
            code_list += self.gen_code(ast_node.test)
            code_list.append(Code(OPCodes.JF, false_label))
            code_list += self.gen_code_statement(ast_node.consequent)
            code_list.append(Code(OPCodes.JMP, end_label))
            code_list.append(false_label)
            if ast_node.alternate is not None:
                code_list += self.gen_code_statement(ast_node.alternate)
                code_list.append(end_label)
        elif isinstance(ast_node, LoopStatement):
            # loop | while
            # a:                     a:
            #    while (<cond>)        <cond>
            #                          JZ b
            #     <statement>          <statement>
            #                          JMP a
            # b:                     b:
            continue_label = Address()
            break_label = Address()
            self.continue_label_list.append(continue_label)
            self.break_label_list.append(break_label)
            code_list.append(continue_label)
            if isinstance(ast_node, WhileStatement):
                code_list += self.gen_code(ast_node.test)
                code_list.append(Code(OPCodes.JF, break_label))
            code_list += self.gen_code_statement(ast_node.body)
            code_list += [
                Code(OPCodes.JMP, continue_label),
                break_label
            ]
            self.continue_label_list.pop()
            self.break_label_list.pop()
        elif isinstance(ast_node, ForStatement):
            # for
            continue_label = Address()
            break_label = Address()
            self.continue_label_list.append(continue_label)
            self.break_label_list.append(break_label)
            code_list += self.gen_code(ast_node.right)
            code_list += [
                Code(OPCodes.FOR),
                continue_label,
                Code(OPCodes.FOR_PRE),
                Code(OPCodes.TOP, ast_node.left1.name),
                Code(OPCodes.JN, break_label),
                Code(OPCodes.GET_TABLE_TOP),
                Code(OPCodes.TOP, ast_node.left2.name),
                Code(OPCodes.POP)
            ]
            code_list += self.gen_code_statement(ast_node.body)
            code_list += [
                Code(OPCodes.JMP, continue_label),
                break_label,
                Code(OPCodes.POP),  # 清除临时指针
                Code(OPCodes.POP),  # 当前 table 出栈
                Code(OPCodes.POP)  # 临时指针出栈
            ]
            self.continue_label_list.pop()
            self.break_label_list.pop()
        elif isinstance(ast_node, BreakStatement):
            # break
            if len(self.break_label_list) == 0:
                raise CodeGeneratorError(ErrorCode.UNSYNTACTIC_BREAK, message=repr(ast_node))
            code_list.append(Code(OPCodes.JMP, self.break_label_list[-1]))
        elif isinstance(ast_node, ContinueStatement):
            # continue
            if len(self.continue_label_list) == 0:
                raise CodeGeneratorError(ErrorCode.UNSYNTACTIC_CONTINUE, message=repr(ast_node))
            code_list.append(Code(OPCodes.JMP, self.continue_label_list[-1]))
        elif isinstance(ast_node, GotoStatement):
            # goto
            for argument in ast_node.argument.arguments:
                code_list += self.gen_code(argument)
            code_list += self.gen_code(ast_node.argument.callee)
            code_list.append(Code(OPCodes.GOTO, len(ast_node.argument.arguments)))
        elif isinstance(ast_node, ReturnStatement):
            # return
            if ast_node.argument is None:
                code_list.append(Code(OPCodes.PUSH_LITERAL, self.add_literal_list(None)))
            else:
                code_list += self.gen_code(ast_node.argument)
            code_list.append(Code(OPCodes.RET))
        elif isinstance(ast_node, GlobalStatement):
            # global
            for argument in ast_node.arguments:
                code_list.append(Code(OPCodes.GLO, argument.name))
        elif isinstance(ast_node, FunctionExpression):
            # func
            func = Function(len(ast_node.params))
            code_list.append(Code(OPCodes.PUSH_LITERAL, self.add_literal_list(func)))
            func.code_list.append(func)
            for param in reversed(ast_node.params):
                func.code_list.append(Code(OPCodes.TOP, param.name))
                func.code_list.append(Code(OPCodes.POP))
            func.code_list += self.gen_code_statement(ast_node.body)
            if not isinstance(func.code_list[-1], Code) or func.code_list[-1].opcode != OPCodes.RET.value:
                func.code_list += [
                    Code(OPCodes.PUSH_LITERAL, self.add_literal_list(None)),
                    Code(OPCodes.RET)
                ]
            self.func_list.append(func)
        elif isinstance(ast_node, TableExpression):
            # table {}
            code_list.append(Code(OPCodes.NEW_TABLE))
            for property_node in ast_node.properties:
                code_list += self.gen_code(property_node.key)
                code_list += self.gen_code(property_node.value)
                code_list.append(Code(OPCodes.SET_TABLE_TOP))
        elif isinstance(ast_node, UnaryExpression):
            # 一元运算
            code_list += self.gen_code(ast_node.argument)
            if ast_node.operator == '+':
                pass
            elif ast_node.operator == '-':
                code_list.append(Code(OPCodes.NEG))
            elif ast_node.operator == '!':
                code_list.append(Code(OPCodes.NOT))
        elif isinstance(ast_node, BinaryExpression):
            # 二元运算
            code_list += self.gen_code(ast_node.left)
            code_list += self.gen_code(ast_node.right)
            code_list.append(Code(binary_operator_to_opcodes[ast_node.operator]))
        elif isinstance(ast_node, AssignmentExpression):
            # 赋值
            if isinstance(ast_node.left, Identifier):
                code_list += self.gen_code(ast_node.right)
                code_list.append(Code(OPCodes.TOP, ast_node.left.name))
            elif isinstance(ast_node.left, MemberExpression):
                code_list += self.gen_code(ast_node.left)
                code_list.pop()
                code_list.pop()
                code_list += self.gen_code(ast_node.right)
                code_list.append(Code(OPCodes.SET_TABLE_TOP))
        elif isinstance(ast_node, MemberExpression):
            # 取成员
            code_list += self.gen_code(ast_node.table)
            if ast_node.computed:
                code_list += self.gen_code(ast_node.property)
            else:
                assert isinstance(ast_node.property, Identifier)
                code_list.append(Code(OPCodes.PUSH_LITERAL, self.add_literal_list(ast_node.property.name)))
            code_list += [
                Code(OPCodes.GET_TABLE_TOP),
                Code(OPCodes.POP)
            ]
        elif isinstance(ast_node, CallExpression):
            # 函数调用
            code_list += self.gen_code(ast_node.callee)
            for argument in ast_node.arguments:
                code_list += self.gen_code(argument)
            code_list.append(Code(OPCodes.CALL, len(ast_node.arguments)))
        return code_list
