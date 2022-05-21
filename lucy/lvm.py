import os
from typing import List, Tuple

from .lucy_data import *
from .lexer import Lexer
from .parser import Parser
from .libs import lib_table
from .exceptions import LVMError, ErrorCode
from .codegen import CodeGenerator, CodeProgram, OPCodes, Function, cmp_op


def _get_code_program(path: str):
    with open(path, 'r', encoding='utf-8') as f:
        return CodeGenerator(Parser(Lexer(f.read())).parse()).generate()


def lucy_type(data: T_Data) -> StringData:
    if isinstance(data, NullData):
        return 'null'
    elif isinstance(data, BooleanData):
        return 'bool'
    elif isinstance(data, IntegerData):
        return 'int'
    elif isinstance(data, FloatData):
        return 'float'
    elif isinstance(data, StringData):
        return 'string'
    elif isinstance(data, TableData):
        return 'table'
    elif isinstance(data, ClosureData):
        return 'function'
    else:
        raise LVMError(ErrorCode.TYPE_ERROR, f'Unknown type {type(data)}')


def lucy_assert(v: T_Data) -> T_Data:
    if isinstance(v, NullData) or v is False:
        raise LVMError(ErrorCode.ASSERT_ERROR)
    else:
        return v


BINARY_OPCODES = {
    OPCodes.ADD: ('__add__', '+'),
    OPCodes.SUB: ('__sub__', '-'),
    OPCodes.MUL: ('__mul__', '*'),
    OPCodes.DIV: ('__div__', '/'),
    OPCodes.MOD: ('__mod__', '%'),
}
COMPARE_OPERATORS = {
    '<': '__lt__',
    '<=': '__le__',
    '==': '__eq__',
    '!=': '__ne__',
    '>': '__gt__',
    '>=': '__ge__',
}


class StackFrame:
    def __init__(self,
                 closure: ClosureData,
                 operate_stack: List[T_Data] = None,
                 return_address: Tuple[int, int] = (0, 0),
                 no_return: bool = False):
        self.closure: ClosureData = closure
        self.operate_stack: List[T_Data] = operate_stack if operate_stack is not None else list()
        self.return_address: Tuple[int, int] = return_address
        self.no_return: bool = no_return
        self.call_flag: bool = False


class LVM:
    def __init__(self,
                 code_program: CodeProgram,
                 module_id: int = 0,
                 package_paths: Dict[str, str] = None,
                 packages: List[CodeProgram] = None):
        if package_paths is None:
            package_paths = dict()
            try:
                libs_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'libs')
                with os.scandir(libs_path) as it:
                    for entry in it:
                        if not entry.name.startswith('.') and not entry.name.startswith('_') and entry.is_file():
                            root, ext = os.path.splitext(entry.name)
                            if ext == '.lucy':
                                package_paths[root] = os.path.abspath(entry.path)
            except NameError:
                pass
        self.package_paths: Dict[str, str] = package_paths
        self.module_id: int = module_id
        if packages is None:
            packages = [code_program]
        self.packages: List[CodeProgram] = packages
        self.builtin_namespace: VariablesDict = VariablesDict({
            'type': ClosureData(function=ExtendFunction(func=lucy_type, params_num=1)),
            'assert': ClosureData(function=ExtendFunction(func=lucy_assert, params_num=1)),
        })
        self.global_stack_frame: StackFrame = StackFrame(ClosureData(module_id=self.module_id, function=None))
        self.call_stack: List[StackFrame] = [self.global_stack_frame]

        self.current_module_id = self.module_id
        self.pc: int = 0

        self.current_code_program = self.packages[self.current_module_id]
        self.current_code = self.current_code_program.code_list[self.pc]
        self.current_operate_stack = self.call_stack[-1].operate_stack
        self.current_variables = self.call_stack[-1].closure.variables
        self.current_return_address = self.call_stack[-1].return_address
        self.current_closure = self.call_stack[-1].closure

    @classmethod
    def run_file(cls, path: str):
        cls(code_program=_get_code_program(path)).run()

    @staticmethod
    def check_type(value: T_Data, data_type: Tuple[type, ...]):
        if not isinstance(value, data_type):
            raise LVMError(ErrorCode.TYPE_ERROR, f'required {data_type}, but {type(value)} was given')

    def run(self):
        def unsupported_operand_type(operator: str):
            raise LVMError(ErrorCode.TYPE_ERROR,
                           f'unsupported operand type(s) for {operator}: {type(arg1)} and {type(arg2)}')

        def number_only_operator(operator: str):
            if isinstance(arg1, IntegerData):
                if not isinstance(arg2, IntegerData):
                    unsupported_operand_type(operator)
            elif isinstance(arg1, FloatData):
                if not isinstance(arg2, FloatData):
                    unsupported_operand_type(operator)
            else:
                unsupported_operand_type(operator)

        while True:
            self.current_code_program = self.packages[self.current_module_id]
            self.current_code = self.current_code_program.code_list[self.pc]
            self.current_operate_stack = self.call_stack[-1].operate_stack
            self.current_variables = self.call_stack[-1].closure.variables
            self.current_return_address = self.call_stack[-1].return_address
            self.current_closure = self.call_stack[-1].closure
            if self.pc >= len(self.current_code_program.code_list):
                break

            if self.current_code.opcode == OPCodes.LOAD_CONST:
                value = self.current_code_program.const_list[self.current_code.argument]
                if isinstance(value, Function):
                    value = ClosureData(module_id=self.module_id,
                                        function=value,
                                        base_closure=self.current_closure if value.is_closure else None,
                                        global_closure=self.global_stack_frame.closure)
                self.current_operate_stack.append(value)
            elif self.current_code.opcode == OPCodes.LOAD_NAME:
                value = self.current_code_program.name_list[self.current_code.argument]
                target = self.current_variables[value]
                if isinstance(target, GlobalReference):
                    target = self.current_closure.global_closure.variables[value]
                if isinstance(target, NullData):
                    closure = self.current_closure.base_closure
                    while closure is not None:
                        target = closure.variables[value]
                        if not isinstance(target, NullData):
                            break
                        closure = closure.base_closure
                if isinstance(target, NullData):
                    if self.current_closure.global_closure is not None:
                        target = self.current_closure.global_closure.variables[value]
                if isinstance(target, NullData):
                    target = self.builtin_namespace[value]
                self.current_operate_stack.append(target)
            elif self.current_code.opcode == OPCodes.STORE:
                value = self.current_code_program.name_list[self.current_code.argument]
                if isinstance(self.current_variables[value], GlobalReference):
                    temp = self.current_closure.global_closure.variables
                else:
                    temp = self.current_variables
                    closure = self.current_closure.base_closure
                    while closure is not None:
                        if not isinstance(closure.variables[value], NullData):
                            temp = closure.variables
                            break
                        closure = closure.base_closure
                if isinstance(self.current_operate_stack[-1], NullData):
                    temp.pop(value, None)
                else:
                    temp[value] = self.current_operate_stack[-1]
                self.current_operate_stack.pop()
            elif self.current_code.opcode == OPCodes.POP:
                self.current_operate_stack.pop()
            elif self.current_code.opcode == OPCodes.DUP:
                self.current_operate_stack.append(self.current_operate_stack[-1])
            elif self.current_code.opcode == OPCodes.DUP_TWO:
                self.current_operate_stack += self.current_operate_stack[-2:]
            elif self.current_code.opcode == OPCodes.ROT_TWO:
                arg1 = self.current_operate_stack.pop()
                arg2 = self.current_operate_stack.pop()
                self.current_operate_stack.append(arg1)
                self.current_operate_stack.append(arg2)
            elif self.current_code.opcode == OPCodes.GLOBAL:
                value = self.current_code_program.name_list[self.current_code.argument]
                self.current_variables[value] = GlobalReference()
            elif self.current_code.opcode == OPCodes.IMPORT:
                temp = self.current_code_program.const_list[self.current_code.argument].split('.')
                if temp[0] in lib_table.keys():
                    value = lib_table[temp[0]]
                elif temp[0] in self.package_paths.keys():
                    code_program = _get_code_program(self.package_paths[temp[0]])
                    self.packages.append(code_program)
                    lvm = self.__class__(code_program=code_program,
                                         module_id=self.module_id + 1,
                                         package_paths=self.package_paths,
                                         packages=self.packages)
                    lvm.run()
                    value = lvm.export_package()
                else:
                    raise LVMError(ErrorCode.IMPORT_ERROR, f'can not find {temp[0]} package')
                for i in temp[1:]:
                    value = value[i]
                    if isinstance(value, NullData):
                        raise LVMError(ErrorCode.IMPORT_ERROR, f'can not find {i} in {value!r}')
                self.current_operate_stack.append(value)
            elif self.current_code.opcode == OPCodes.IMPORT_FROM:
                arg1 = self.current_operate_stack[-1]
                self.check_type(arg1, (TableData,))
                self.current_operate_stack.append(
                    arg1[self.current_code_program.const_list[self.current_code.argument]]
                )
            elif self.current_code.opcode == OPCodes.IMPORT_STAR:
                arg1 = self.current_operate_stack[-1]
                self.check_type(arg1, (TableData,))
                for key, value in arg1.items():
                    if isinstance(key, StringData) and not key.startswith('_'):
                        self.current_variables[key] = value
            elif self.current_code.opcode == OPCodes.BUILD_TABLE:
                temp = []
                for i in range(self.current_code.argument):
                    temp.append(self.current_operate_stack.pop())
                    temp.append(self.current_operate_stack.pop())
                table = TableData()
                for i in range(self.current_code.argument):
                    arg1 = temp.pop()
                    arg2 = temp.pop()
                    self.check_type(arg1, HASHABLE_DATA_TYPE)
                    table[arg1] = arg2
                self.current_operate_stack.append(table)
            elif self.current_code.opcode == OPCodes.GET_ATTR or self.current_code.opcode == OPCodes.GET_ITEM:
                table_key = ''
                if self.current_code.opcode == OPCodes.GET_ATTR:
                    table_key = '__getattr__'
                elif self.current_code.opcode == OPCodes.GET_ITEM:
                    table_key = '__getitem__'
                arg2 = self.current_operate_stack.pop()
                arg1 = self.current_operate_stack.pop()
                self.check_type(arg1, (TableData,))
                self.check_type(arg2, HASHABLE_DATA_TYPE)
                if isinstance(arg1[table_key], ClosureData):
                    self.current_operate_stack.append(arg1[table_key])
                    self.current_operate_stack.append(arg1)
                    self.current_operate_stack.append(arg2)
                    self.code_call(arg_num=2)
                    continue
                else:
                    self.current_operate_stack.append(arg1[arg2])
            elif self.current_code.opcode == OPCodes.SET_ATTR or self.current_code.opcode == OPCodes.SET_ITEM:
                table_key = ''
                if self.current_code.opcode == OPCodes.SET_ATTR:
                    table_key = '__setattr__'
                elif self.current_code.opcode == OPCodes.SET_ITEM:
                    table_key = '__setitem__'
                arg3 = self.current_operate_stack.pop()
                arg2 = self.current_operate_stack.pop()
                arg1 = self.current_operate_stack[-1]
                self.check_type(arg1, (TableData,))
                self.check_type(arg2, HASHABLE_DATA_TYPE)
                if isinstance(arg1[table_key], ClosureData):
                    self.current_operate_stack.append(arg1[table_key])
                    self.current_operate_stack.append(arg1)
                    self.current_operate_stack.append(arg2)
                    self.current_operate_stack.append(arg3)
                    self.code_call(arg_num=3, no_return=True)
                    continue
                else:
                    arg1[arg2] = arg3
            elif self.current_code.opcode == OPCodes.FOR:
                if self.call_stack[-1].call_flag:
                    self.call_stack[-1].call_flag = False
                    if isinstance(self.current_operate_stack[-1], NullData):
                        self.current_operate_stack.pop()
                        self.pc = self.current_code.argument
                        continue
                else:
                    self.call_stack[-1].call_flag = True
                    self.code_call(arg_num=0, return_pc=self.pc, pop=False)
                    continue
            elif self.current_code.opcode == OPCodes.NEG:
                if self.call_stack[-1].call_flag:
                    self.call_stack[-1].call_flag = False
                else:
                    arg1 = self.current_operate_stack.pop()
                    if isinstance(arg1, TableData) and isinstance(arg1['__neg__'], ClosureData):
                        self.current_operate_stack.append(arg1['__neg__'])
                        self.current_operate_stack.append(arg1)
                        self.call_stack[-1].call_flag = True
                        self.code_call(arg_num=1, return_pc=self.pc)
                        continue
                    else:
                        self.check_type(arg1, (IntegerData, FloatData))
                        self.current_operate_stack.append(-arg1)
            elif self.current_code.opcode == OPCodes.NOT:
                arg1 = self.current_operate_stack.pop()
                self.check_type(arg1, (BooleanData,))
                self.current_operate_stack.append(not arg1)
            elif self.current_code.opcode == OPCodes.GET_LEN:
                if self.call_stack[-1].call_flag:
                    self.call_stack[-1].call_flag = False
                else:
                    arg1 = self.current_operate_stack.pop()
                    if isinstance(arg1, TableData) and isinstance(arg1['__len__'], ClosureData):
                        self.current_operate_stack.append(arg1['__len__'])
                        self.current_operate_stack.append(arg1)
                        self.call_stack[-1].call_flag = True
                        self.code_call(arg_num=1, return_pc=self.pc)
                        continue
                    else:
                        self.check_type(arg1, (StringData, TableData))
                        self.current_operate_stack.append(len(arg1))
            elif self.current_code.opcode in BINARY_OPCODES.keys():
                table_key, operator_name = BINARY_OPCODES[self.current_code.opcode]

                if self.call_stack[-1].call_flag:
                    self.call_stack[-1].call_flag = False
                else:
                    arg2 = self.current_operate_stack.pop()
                    arg1 = self.current_operate_stack.pop()

                    if isinstance(arg1, TableData) and isinstance(arg1[table_key], ClosureData):
                        self.current_operate_stack.append(arg1[table_key])
                        self.current_operate_stack.append(arg1)
                        self.current_operate_stack.append(arg2)
                        self.call_stack[-1].call_flag = True
                        self.code_call(arg_num=2, return_pc=self.pc)
                        continue
                    elif self.current_code.opcode == OPCodes.ADD and isinstance(arg1, StringData):
                        if not isinstance(arg2, StringData):
                            unsupported_operand_type('+')
                    else:
                        number_only_operator(operator_name)

                    if self.current_code.opcode == OPCodes.ADD:
                        self.current_operate_stack.append(arg1 + arg2)
                    elif self.current_code.opcode == OPCodes.SUB:
                        self.current_operate_stack.append(arg1 - arg2)
                    elif self.current_code.opcode == OPCodes.MUL:
                        self.current_operate_stack.append(arg1 * arg2)
                    elif self.current_code.opcode == OPCodes.DIV:
                        if isinstance(arg1, IntegerData):
                            self.current_operate_stack.append(arg1 // arg2)
                        elif isinstance(arg1, FloatData):
                            self.current_operate_stack.append(arg1 / arg2)
                    elif self.current_code.opcode == OPCodes.MOD:
                        self.current_operate_stack.append(arg1 % arg2)

            elif self.current_code.opcode == OPCodes.COMPARE_OP:
                operator_name = cmp_op[self.current_code.argument]
                table_key = COMPARE_OPERATORS[operator_name]

                if self.call_stack[-1].call_flag:
                    self.call_stack[-1].call_flag = False
                else:
                    arg2 = self.current_operate_stack.pop()
                    arg1 = self.current_operate_stack.pop()

                    if isinstance(arg1, TableData) and isinstance(arg1[table_key], ClosureData):
                        self.current_operate_stack.append(arg1[table_key])
                        self.current_operate_stack.append(arg1)
                        self.current_operate_stack.append(arg2)
                        self.call_stack[-1].call_flag = True
                        self.code_call(arg_num=2, return_pc=self.pc)
                        continue
                    elif operator_name != '==' and operator_name != '!=':
                        number_only_operator(operator_name)

                    if operator_name == '==':
                        self.current_operate_stack.append(arg1 == arg2)
                    elif operator_name == '!=':
                        self.current_operate_stack.append(arg1 != arg2)
                    elif operator_name == '<':
                        self.current_operate_stack.append(arg1 < arg2)
                    elif operator_name == '<=':
                        self.current_operate_stack.append(arg1 <= arg2)
                    elif operator_name == '>':
                        self.current_operate_stack.append(arg1 > arg2)
                    elif operator_name == '>=':
                        self.current_operate_stack.append(arg1 >= arg2)

            elif self.current_code.opcode == OPCodes.IS:
                arg2 = self.current_operate_stack.pop()
                arg1 = self.current_operate_stack.pop()
                self.current_operate_stack.append(arg1 is arg2)
            elif self.current_code.opcode == OPCodes.JUMP:
                self.pc = self.current_code.argument
                continue
            elif self.current_code.opcode == OPCodes.JUMP_IF_TRUE:
                arg = self.current_operate_stack.pop()
                self.check_type(arg, (BooleanData,))
                if arg is True:
                    self.pc = self.current_code.argument
                    continue
            elif self.current_code.opcode == OPCodes.JUMP_IF_FALSE:
                arg = self.current_operate_stack.pop()
                self.check_type(arg, (BooleanData,))
                if arg is False:
                    self.pc = self.current_code.argument
                    continue
            elif self.current_code.opcode == OPCodes.JUMP_IF_TRUE_OR_POP:
                arg = self.current_operate_stack[-1]
                self.check_type(arg, (BooleanData,))
                if arg is True:
                    self.pc = self.current_code.argument
                    continue
                else:
                    self.current_operate_stack.pop()
            elif self.current_code.opcode == OPCodes.JUMP_IF_FALSE_OR_POP:
                arg = self.current_operate_stack[-1]
                self.check_type(arg, (BooleanData,))
                if arg is False:
                    self.pc = self.current_code.argument
                    continue
                else:
                    self.current_operate_stack.pop()
            elif self.current_code.opcode == OPCodes.CALL:
                self.code_call()
                continue
            elif self.current_code.opcode == OPCodes.GOTO:
                self.call_stack.pop()
                self.code_call()
                continue
            elif self.current_code.opcode == OPCodes.RETURN:
                return_value = self.current_operate_stack.pop()
                self.current_module_id, self.pc = self.current_return_address
                temp = self.call_stack.pop()
                if len(self.call_stack) == 0:
                    break
                if not temp.no_return:
                    self.call_stack[-1].operate_stack.append(return_value)
                continue
            self.pc += 1

    def code_call(self, arg_num: int = None, return_pc: int = None, pop: bool = True, no_return: bool = False):
        if arg_num is None:
            arg_num = self.current_code.argument
        if return_pc is None:
            return_pc = self.pc + 1

        arguments_list = [self.current_operate_stack.pop() for _ in range(arg_num)]

        if pop:
            closure = self.current_operate_stack.pop()
        else:
            # 不弹出栈顶的 closure，用于 for
            closure = self.current_operate_stack[-1]

        if isinstance(closure, TableData) and isinstance(closure['__call__'], ClosureData):
            arguments_list.append(closure)
            closure = closure['__call__']
        if not isinstance(closure, ClosureData):
            raise LVMError(ErrorCode.TYPE_ERROR, f'{type(closure)} is not callable')

        if len(arguments_list) != closure.function.params_num:
            raise LVMError(
                ErrorCode.CALL_ERROR,
                f'{closure} require {closure.function.params_num} arguments, but {len(arguments_list)} was given'
            )

        if isinstance(closure.function, ExtendFunction):
            try:
                return_value = closure.function.func(*reversed(arguments_list))
            except Exception as e:
                raise LVMError(
                    ErrorCode.EXTEND_FUNCTION_ERROR,
                    f'Extend function {closure.function!r} raise exception {e!r}'
                )
            if not isinstance(return_value, LUCY_DATA_TYPE):
                raise LVMError(
                    ErrorCode.EXTEND_FUNCTION_ERROR,
                    f'Extend function {closure.function!r} return value is not a lucy data'
                )
            self.current_operate_stack.append(return_value)
            self.pc = return_pc
        else:
            closure = ClosureData(module_id=closure.module_id,
                                  function=closure.function,
                                  base_closure=closure.base_closure,
                                  global_closure=closure.global_closure)
            self.call_stack.append(StackFrame(
                closure=closure,
                operate_stack=arguments_list,
                return_address=(self.current_module_id, return_pc),
                no_return=no_return,
            ))
            self.current_module_id = closure.module_id
            self.pc = closure.function.address

    def export_package(self) -> TableData:
        return self.global_stack_frame.closure.variables
