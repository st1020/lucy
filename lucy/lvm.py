from typing import List, Dict, Union, Optional, Tuple

from .exceptions import LVMError, ErrorCode
from .codegen import CodeProgram, OPCodes, Function, cmp_op

NullData = type(None)
BooleanData = bool
IntegerData = int
FloatData = float
StringData = str

HASHABLE_DATA_TYPE = (NullData, BooleanData, IntegerData, FloatData, StringData)


class TableData(Dict['T_Data', 'T_Data']):
    def __getitem__(self, item):
        try:
            return super().__getitem__(item)
        except KeyError:
            return NullData()

    def __setitem__(self, key, value):
        if isinstance(value, NullData):
            try:
                del self[key]
            except KeyError:
                pass
        else:
            super().__setitem__(key, value)


class VariablesDict(TableData, Dict[str, Union['T_Data', 'GlobalReference']]):
    pass


class ClosureData:
    def __init__(self, function: Optional[Function], base_closure: Optional['ClosureData'] = None):
        self.function: Optional[Function] = function
        self.base_closure: Optional[ClosureData] = base_closure
        self._variables: Optional[VariablesDict] = None

    @property
    def variables(self):
        if self._variables is None:
            self._variables = VariablesDict()
        return self._variables


T_Data = Union[NullData, BooleanData, IntegerData, FloatData, StringData, TableData, ClosureData]


class GlobalReference:
    obj = None

    def __new__(cls, *args, **kwargs):
        if cls.obj is None:
            cls.obj = super().__new__(cls)
        return cls.obj


class StackFrame:
    def __init__(self, closure: ClosureData, operate_stack: List[T_Data] = None, return_address: int = 0):
        self.closure: ClosureData = closure
        self.operate_stack: List[T_Data] = operate_stack if operate_stack is not None else list()
        self.return_address: int = return_address


class LVM:
    def __init__(self, code_program: CodeProgram):
        self.code_program: CodeProgram = code_program
        self.pc: int = 0
        self.global_stack_frame: StackFrame = StackFrame(ClosureData(None))
        self.call_stack: List[StackFrame] = [self.global_stack_frame]

        self.current_code = self.code_program.code_list[self.pc]
        self.current_operate_stack = self.call_stack[-1].operate_stack
        self.current_variables = self.call_stack[-1].closure.variables
        self.current_return_address = self.call_stack[-1].return_address
        self.current_closure = self.call_stack[-1].closure
        self.call_flag: bool = False

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

        while self.pc < len(self.code_program.code_list):
            self.current_code = self.code_program.code_list[self.pc]
            self.current_operate_stack = self.call_stack[-1].operate_stack
            self.current_variables = self.call_stack[-1].closure.variables
            self.current_return_address = self.call_stack[-1].return_address
            self.current_closure = self.call_stack[-1].closure

            if self.current_code.opcode == OPCodes.LOAD_CONST:
                value = self.code_program.const_list[self.current_code.argument]
                if isinstance(value, Function):
                    value = ClosureData(function=value, base_closure=self.current_closure if value.is_closure else None)
                self.current_operate_stack.append(value)
            elif self.current_code.opcode == OPCodes.LOAD_NAME:
                value = self.code_program.name_list[self.current_code.argument]
                target = self.current_variables[value]
                if isinstance(target, GlobalReference):
                    target = self.global_stack_frame.closure.variables[value]
                if isinstance(target, NullData):
                    closure = self.current_closure.base_closure
                    while closure is not None:
                        target = closure.variables[value]
                        if not isinstance(target, NullData):
                            break
                        closure = closure.base_closure
                self.current_operate_stack.append(target)
            elif self.current_code.opcode == OPCodes.STORE:
                self.code_store()
            elif self.current_code.opcode == OPCodes.POP:
                self.current_operate_stack.pop()
            elif self.current_code.opcode == OPCodes.STORE_POP:
                self.code_store()
                self.current_operate_stack.pop()
            elif self.current_code.opcode == OPCodes.GLOBAL:
                value = self.code_program.name_list[self.current_code.argument]
                self.current_variables[value] = GlobalReference()
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
            elif self.current_code.opcode == OPCodes.GET_TABLE:
                arg2 = self.current_operate_stack.pop()
                arg1 = self.current_operate_stack.pop()
                self.check_type(arg1, (TableData,))
                self.check_type(arg2, HASHABLE_DATA_TYPE)
                self.current_operate_stack.append(arg1[arg2])
            elif self.current_code.opcode == OPCodes.SET_TABLE:
                arg3 = self.current_operate_stack.pop()
                arg2 = self.current_operate_stack.pop()
                arg1 = self.current_operate_stack[-1]
                self.check_type(arg1, (TableData,))
                self.check_type(arg2, HASHABLE_DATA_TYPE)
                arg1[arg2] = arg3
            elif self.current_code.opcode == OPCodes.FOR:
                if self.call_flag:
                    self.call_flag = False
                    if isinstance(self.current_operate_stack[-1], NullData):
                        self.current_operate_stack.pop()
                        self.pc = self.current_code.argument
                        continue
                else:
                    self.call_flag = True
                    self.code_call(arg_num=0, return_address=self.pc, pop=False)
                    continue
            elif self.current_code.opcode == OPCodes.NEG:
                arg1 = self.current_operate_stack.pop()
                self.check_type(arg1, (IntegerData, FloatData))
                self.current_operate_stack.append(-arg1)
            elif self.current_code.opcode == OPCodes.NOT:
                arg1 = self.current_operate_stack.pop()
                self.check_type(arg1, (BooleanData,))
                self.current_operate_stack.append(not arg1)
            elif self.current_code.opcode == OPCodes.ADD:
                arg2 = self.current_operate_stack.pop()
                arg1 = self.current_operate_stack.pop()
                if isinstance(arg1, IntegerData):
                    if not isinstance(arg2, IntegerData):
                        unsupported_operand_type('+')
                elif isinstance(arg1, FloatData):
                    if not isinstance(arg2, FloatData):
                        unsupported_operand_type('+')
                elif isinstance(arg1, StringData):
                    if not isinstance(arg2, StringData):
                        unsupported_operand_type('+')
                else:
                    unsupported_operand_type('+')
                self.current_operate_stack.append(arg1 + arg2)
            elif self.current_code.opcode == OPCodes.SUB:
                arg2 = self.current_operate_stack.pop()
                arg1 = self.current_operate_stack.pop()
                number_only_operator('-')
                self.current_operate_stack.append(arg1 - arg2)
            elif self.current_code.opcode == OPCodes.MUL:
                arg2 = self.current_operate_stack.pop()
                arg1 = self.current_operate_stack.pop()
                number_only_operator('*')
                self.current_operate_stack.append(arg1 * arg2)
            elif self.current_code.opcode == OPCodes.DIV:
                arg2 = self.current_operate_stack.pop()
                arg1 = self.current_operate_stack.pop()
                if isinstance(arg1, IntegerData):
                    if not isinstance(arg2, IntegerData):
                        unsupported_operand_type('/')
                    self.current_operate_stack.append(arg1 // arg2)
                elif isinstance(arg1, FloatData):
                    if not isinstance(arg2, FloatData):
                        unsupported_operand_type('/')
                    self.current_operate_stack.append(arg1 / arg2)
                else:
                    unsupported_operand_type('/')
            elif self.current_code.opcode == OPCodes.MOD:
                arg2 = self.current_operate_stack.pop()
                arg1 = self.current_operate_stack.pop()
                number_only_operator('%')
                self.current_operate_stack.append(arg1 % arg2)
            elif self.current_code.opcode == OPCodes.COMPARE_OP:
                arg2 = self.current_operate_stack.pop()
                arg1 = self.current_operate_stack.pop()
                if cmp_op[self.current_code.argument] != '==' and cmp_op[self.current_code.argument] != '!=':
                    number_only_operator(cmp_op[self.current_code.argument])
                if cmp_op[self.current_code.argument] == '==':
                    self.current_operate_stack.append(arg1 == arg2)
                elif cmp_op[self.current_code.argument] == '!=':
                    self.current_operate_stack.append(arg1 != arg2)
                elif cmp_op[self.current_code.argument] == '<':
                    self.current_operate_stack.append(arg1 < arg2)
                elif cmp_op[self.current_code.argument] == '<=':
                    self.current_operate_stack.append(arg1 <= arg2)
                elif cmp_op[self.current_code.argument] == '>':
                    self.current_operate_stack.append(arg1 > arg2)
                elif cmp_op[self.current_code.argument] == '>=':
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
                self.pc = self.current_return_address
                self.call_stack.pop()
                if len(self.call_stack) == 0:
                    break
                self.call_stack[-1].operate_stack.append(return_value)
                continue
            self.pc += 1

    def code_store(self):
        value = self.code_program.name_list[self.current_code.argument]
        if isinstance(self.current_variables[value], GlobalReference):
            temp = self.global_stack_frame.closure.variables
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

    def code_call(self, arg_num: int = None, return_address: int = None, pop: bool = True):
        if arg_num is None:
            arg_num = self.current_code.argument
        if return_address is None:
            return_address = self.pc + 1

        arguments_list = [self.current_operate_stack.pop() for _ in range(arg_num)]
        if pop:
            closure = self.current_operate_stack.pop()
        else:
            # 不弹出栈顶的 closure，用于 for
            closure = self.current_operate_stack[-1]
        if isinstance(closure, ClosureData):
            closure = ClosureData(function=closure.function, base_closure=closure.base_closure)
        else:
            raise LVMError(ErrorCode.TYPE_ERROR, f'{type(closure)} is not callable.')
        self.call_stack.append(StackFrame(
            closure=closure,
            operate_stack=arguments_list,
            return_address=return_address
        ))
        self.pc = closure.function.address
