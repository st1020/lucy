from collections import defaultdict
from typing import List, Dict, Union, Optional

from .exceptions import LVMError, ErrorCode
from .codegen import CodeProgram, OPCodes, Function

NullData = type(None)
BooleanData = bool
IntegerData = int
FloatData = float
StringData = str


class TableData(defaultdict, Dict['T_Data', 'T_Data']):
    def __init__(self):
        super().__init__(NullData)

    def __repr__(self):
        return repr(dict(self))


class VariablesDict(TableData, Dict[str, Union['T_Data', 'GlobalReference', 'NonlocalReference']]):
    pass


class ClosureData:
    def __init__(self,
                 function: Function,
                 base_closure: Optional['ClosureData'],
                 variables: Optional[VariablesDict] = None):
        self.function: Function = function
        self.base_closure: Optional[ClosureData] = base_closure
        self._variables: Optional[VariablesDict] = variables

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


class NonlocalReference:
    def __init__(self, ref_closure: ClosureData):
        self.ref_closure = ref_closure


class StackFrame:
    def __init__(self,
                 closure: Optional[ClosureData] = None,
                 operate_stack: List[T_Data] = None,
                 return_address: int = 0):
        self.closure: Optional[ClosureData] = closure
        self.variables: VariablesDict = self.closure.variables if self.closure is not None else VariablesDict()
        self.operate_stack: List[T_Data] = operate_stack if operate_stack is not None else list()
        self.return_address: int = return_address


class LVM:
    def __init__(self, code_program: CodeProgram):
        self.code_program: CodeProgram = code_program
        self.code_list = self.code_program.code_list
        self.literal_list = self.code_program.literal_list
        self.pc: int = 0
        self.global_stack_frame: StackFrame = StackFrame()
        self.call_stack: List[StackFrame] = [self.global_stack_frame]

    def run(self):
        def check_table_index(value_):
            if isinstance(value_, str):
                return value_
            elif isinstance(value_, int) or isinstance(value_, float):
                return str(value_)
            else:
                raise TypeError('table index must be string or number')

        while self.pc < len(self.code_list):
            current_opcode: OPCodes = self.code_list[self.pc].opcode
            current_argument = self.code_list[self.pc].argument

            current_operate_stack = self.call_stack[-1].operate_stack
            current_variables = self.call_stack[-1].variables
            current_return_address = self.call_stack[-1].return_address
            current_closure = self.call_stack[-1].closure

            if current_opcode == OPCodes.PUSH_LITERAL:
                value = self.literal_list[current_argument]
                if isinstance(value, Function):
                    value = ClosureData(function=value, base_closure=current_closure)
                current_operate_stack.append(value)
            elif current_opcode == OPCodes.PUSH:
                target = current_variables[current_argument]
                if isinstance(target, GlobalReference):
                    target = self.global_stack_frame.variables[current_argument]
                elif isinstance(target, NonlocalReference):
                    target = target.ref_closure.variables[current_argument]
                current_operate_stack.append(target)
            elif current_opcode == OPCodes.TOP:
                if isinstance(current_variables[current_argument], GlobalReference):
                    temp = self.global_stack_frame.variables
                elif isinstance(current_variables[current_argument], NonlocalReference):
                    temp = current_variables[current_argument].ref_closure.variables
                else:
                    temp = current_variables
                if isinstance(current_operate_stack[-1], NullData):
                    temp.pop(current_argument, None)
                else:
                    temp[current_argument] = current_operate_stack[-1]
            elif current_opcode == OPCodes.POP:
                current_operate_stack.pop()
            elif current_opcode == OPCodes.GLOBAL:
                current_variables[current_argument] = GlobalReference()
            elif current_opcode == OPCodes.NONLOCAL:
                closure = current_closure.base_closure
                while closure is not None:
                    if not isinstance(closure.variables[current_argument], NullData):
                        break
                    closure = closure.base_closure
                if closure is None:
                    raise LVMError(ErrorCode.NONLOCAL_ERROR)
                current_variables[current_argument] = NonlocalReference(closure)
            elif current_opcode == OPCodes.NEW_TABLE:
                current_operate_stack.append(TableData())
            elif current_opcode == OPCodes.GET_TABLE:
                arg2 = current_operate_stack.pop()
                arg1 = current_operate_stack.pop()
                current_operate_stack.append(arg1[check_table_index(arg2)])
            elif current_opcode == OPCodes.GET_TABLE_TOP:
                arg2 = current_operate_stack.pop()
                arg1 = current_operate_stack[-1]
                current_operate_stack.append(arg1[check_table_index(arg2)])
            elif current_opcode == OPCodes.SET_TABLE_TOP:
                arg3 = current_operate_stack.pop()
                arg2 = current_operate_stack.pop()
                arg1 = current_operate_stack[-1]
                arg1[check_table_index(arg2)] = arg3
            elif current_opcode == OPCodes.FOR:
                temp = current_operate_stack.pop()
                current_operate_stack.append(0)
                current_operate_stack.append(temp)
            elif current_opcode == OPCodes.FOR_PRE:
                if current_operate_stack[-2] < len(current_operate_stack[-1]):
                    key = list(current_operate_stack[-1].keys())[current_operate_stack[-2]]
                else:
                    key = None
                current_operate_stack[-2] += 1
                current_operate_stack.append(key)
            elif current_opcode == OPCodes.NEG:
                current_operate_stack.append(-current_operate_stack.pop())
            elif current_opcode == OPCodes.NOT:
                current_operate_stack.append(not current_operate_stack.pop())
            elif current_opcode == OPCodes.ADD:
                arg2 = current_operate_stack.pop()
                arg1 = current_operate_stack.pop()
                current_operate_stack.append(arg1 + arg2)
            elif current_opcode == OPCodes.SUB:
                arg2 = current_operate_stack.pop()
                arg1 = current_operate_stack.pop()
                current_operate_stack.append(arg1 - arg2)
            elif current_opcode == OPCodes.MUL:
                arg2 = current_operate_stack.pop()
                arg1 = current_operate_stack.pop()
                current_operate_stack.append(arg1 * arg2)
            elif current_opcode == OPCodes.DIV:
                arg2 = current_operate_stack.pop()
                arg1 = current_operate_stack.pop()
                current_operate_stack.append(arg1 / arg2)
            elif current_opcode == OPCodes.MOD:
                arg2 = current_operate_stack.pop()
                arg1 = current_operate_stack.pop()
                current_operate_stack.append(arg1 % arg2)
            elif current_opcode == OPCodes.AND:
                arg2 = current_operate_stack.pop()
                arg1 = current_operate_stack.pop()
                current_operate_stack.append(arg1 and arg2)
            elif current_opcode == OPCodes.OR:
                arg2 = current_operate_stack.pop()
                arg1 = current_operate_stack.pop()
                current_operate_stack.append(arg1 or arg2)
            elif current_opcode == OPCodes.EQ:
                arg2 = current_operate_stack.pop()
                arg1 = current_operate_stack.pop()
                current_operate_stack.append(arg1 == arg2)
            elif current_opcode == OPCodes.NE:
                arg2 = current_operate_stack.pop()
                arg1 = current_operate_stack.pop()
                current_operate_stack.append(arg1 != arg2)
            elif current_opcode == OPCodes.LT:
                arg2 = current_operate_stack.pop()
                arg1 = current_operate_stack.pop()
                current_operate_stack.append(arg1 < arg2)
            elif current_opcode == OPCodes.LE:
                arg2 = current_operate_stack.pop()
                arg1 = current_operate_stack.pop()
                current_operate_stack.append(arg1 <= arg2)
            elif current_opcode == OPCodes.GT:
                arg2 = current_operate_stack.pop()
                arg1 = current_operate_stack.pop()
                current_operate_stack.append(arg1 > arg2)
            elif current_opcode == OPCodes.GE:
                arg2 = current_operate_stack.pop()
                arg1 = current_operate_stack.pop()
                current_operate_stack.append(arg1 >= arg2)
            elif current_opcode == OPCodes.JMP:
                self.pc = current_argument
                continue
            elif current_opcode == OPCodes.JT:
                if current_operate_stack.pop() is True:
                    self.pc = current_argument
                    continue
            elif current_opcode == OPCodes.JF:
                if current_operate_stack.pop() is False:
                    self.pc = current_argument
                    continue
            elif current_opcode == OPCodes.JN:
                if current_operate_stack[-1] is None:
                    self.pc = current_argument
                    continue
            elif current_opcode == OPCodes.CALL:
                arguments_list = [current_operate_stack.pop() for _ in range(current_argument)]
                closure = current_operate_stack.pop()
                if isinstance(closure, ClosureData):
                    closure = ClosureData(function=closure.function, base_closure=closure.base_closure)
                else:
                    raise LVMError(ErrorCode.TYPE_ERROR, f'{type(closure)} is not callable.')
                self.call_stack.append(StackFrame(
                    closure=closure,
                    operate_stack=arguments_list,
                    return_address=self.pc + 1
                ))
                self.pc = closure.function.address
                continue
            elif current_opcode == OPCodes.GOTO:
                self.call_stack.pop()
                arguments_list = [current_operate_stack.pop() for _ in range(current_argument)]
                closure = current_operate_stack.pop()
                if isinstance(closure, ClosureData):
                    closure = ClosureData(function=closure.function, base_closure=closure.base_closure)
                else:
                    raise LVMError(ErrorCode.TYPE_ERROR, f'{type(closure)} is not callable')
                self.call_stack.append(StackFrame(
                    closure=closure,
                    operate_stack=arguments_list,
                    return_address=self.pc + 1
                ))
                self.pc = closure.function.address
                continue
            elif current_opcode == OPCodes.RET:
                return_value = current_operate_stack.pop()
                self.pc = current_return_address
                self.call_stack.pop()
                self.call_stack[-1].operate_stack.append(return_value)
                continue
            elif current_opcode == OPCodes.EXIT:
                break
            self.pc += 1
