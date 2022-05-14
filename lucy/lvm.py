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

    @staticmethod
    def check_type(value: T_Data, data_type: Tuple[type, ...]):
        if not isinstance(value, data_type):
            raise LVMError(ErrorCode.TYPE_ERROR, f'required {data_type}, but {type(value)} was given')

    def run(self):
        def unsupported_operand_type(operator: str):
            raise LVMError(ErrorCode.TYPE_ERROR,
                           f'unsupported operand type(s) for {operator}: {type(arg1)} and {type(arg2)}')

        def bool_only_operator(operator: str):
            if isinstance(arg1, BooleanData):
                if not isinstance(arg2, BooleanData):
                    unsupported_operand_type(operator)
            else:
                unsupported_operand_type(operator)

        def number_only_operator(operator: str):
            if isinstance(arg1, IntegerData):
                if not isinstance(arg2, IntegerData):
                    unsupported_operand_type(operator)
            elif isinstance(arg1, FloatData):
                if not isinstance(arg2, FloatData):
                    unsupported_operand_type(operator)
            else:
                unsupported_operand_type(operator)

        while self.pc < len(self.code_list):
            current_opcode: OPCodes = self.code_list[self.pc].opcode
            current_argument = self.code_list[self.pc].argument

            current_operate_stack = self.call_stack[-1].operate_stack
            current_variables = self.call_stack[-1].variables
            current_return_address = self.call_stack[-1].return_address
            current_closure = self.call_stack[-1].closure

            if current_opcode == OPCodes.LOAD_CONST:
                value = self.literal_list[current_argument]
                if isinstance(value, Function):
                    value = ClosureData(function=value,
                                        base_closure=current_closure if value.should_closure else None)
                current_operate_stack.append(value)
            elif current_opcode == OPCodes.LOAD_NAME:
                target = current_variables[current_argument]
                if isinstance(target, GlobalReference):
                    target = self.global_stack_frame.variables[current_argument]
                elif isinstance(target, NonlocalReference):
                    target = target.ref_closure.variables[current_argument]
                current_operate_stack.append(target)
            elif current_opcode == OPCodes.STORE:
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
                self.check_type(arg1, (TableData,))
                self.check_type(arg2, HASHABLE_DATA_TYPE)
                current_operate_stack.append(arg1[arg2])
            elif current_opcode == OPCodes.GET_TABLE_TOP:
                arg2 = current_operate_stack.pop()
                arg1 = current_operate_stack[-1]
                self.check_type(arg1, (TableData,))
                self.check_type(arg2, HASHABLE_DATA_TYPE)
                current_operate_stack.append(arg1[arg2])
            elif current_opcode == OPCodes.SET_TABLE_TOP:
                arg3 = current_operate_stack.pop()
                arg2 = current_operate_stack.pop()
                arg1 = current_operate_stack[-1]
                self.check_type(arg1, (TableData,))
                self.check_type(arg2, HASHABLE_DATA_TYPE)
                arg1[arg2] = arg3
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
                arg1 = current_operate_stack.pop()
                self.check_type(arg1, (IntegerData, FloatData))
                current_operate_stack.append(-arg1)
            elif current_opcode == OPCodes.NOT:
                arg1 = current_operate_stack.pop()
                self.check_type(arg1, (BooleanData,))
                current_operate_stack.append(not arg1)
            elif current_opcode == OPCodes.ADD:
                arg2 = current_operate_stack.pop()
                arg1 = current_operate_stack.pop()
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
                current_operate_stack.append(arg1 + arg2)
            elif current_opcode == OPCodes.SUB:
                arg2 = current_operate_stack.pop()
                arg1 = current_operate_stack.pop()
                number_only_operator('-')
                current_operate_stack.append(arg1 - arg2)
            elif current_opcode == OPCodes.MUL:
                arg2 = current_operate_stack.pop()
                arg1 = current_operate_stack.pop()
                number_only_operator('*')
                current_operate_stack.append(arg1 * arg2)
            elif current_opcode == OPCodes.DIV:
                arg2 = current_operate_stack.pop()
                arg1 = current_operate_stack.pop()
                if isinstance(arg1, IntegerData):
                    if not isinstance(arg2, IntegerData):
                        unsupported_operand_type('/')
                    current_operate_stack.append(arg1 // arg2)
                elif isinstance(arg1, FloatData):
                    if not isinstance(arg2, FloatData):
                        unsupported_operand_type('/')
                    current_operate_stack.append(arg1 / arg2)
                else:
                    unsupported_operand_type('/')
            elif current_opcode == OPCodes.MOD:
                arg2 = current_operate_stack.pop()
                arg1 = current_operate_stack.pop()
                number_only_operator('%')
                current_operate_stack.append(arg1 % arg2)
            elif current_opcode == OPCodes.AND:
                arg2 = current_operate_stack.pop()
                arg1 = current_operate_stack.pop()
                bool_only_operator('&&')
                current_operate_stack.append(arg1 and arg2)
            elif current_opcode == OPCodes.OR:
                arg2 = current_operate_stack.pop()
                arg1 = current_operate_stack.pop()
                bool_only_operator('||')
                current_operate_stack.append(arg1 or arg2)
            elif current_opcode == OPCodes.COMPARE_OP:
                arg2 = current_operate_stack.pop()
                arg1 = current_operate_stack.pop()
                if cmp_op[current_argument] != '==' and cmp_op[current_argument] != '!=':
                    number_only_operator(cmp_op[current_argument])
                if cmp_op[current_argument] == '==':
                    current_operate_stack.append(arg1 == arg2)
                elif cmp_op[current_argument] == '!=':
                    current_operate_stack.append(arg1 != arg2)
                elif cmp_op[current_argument] == '<':
                    current_operate_stack.append(arg1 < arg2)
                elif cmp_op[current_argument] == '<=':
                    current_operate_stack.append(arg1 <= arg2)
                elif cmp_op[current_argument] == '>':
                    current_operate_stack.append(arg1 > arg2)
                elif cmp_op[current_argument] == '>=':
                    current_operate_stack.append(arg1 >= arg2)
            elif current_opcode == OPCodes.IS:
                arg2 = current_operate_stack.pop()
                arg1 = current_operate_stack.pop()
                current_operate_stack.append(arg1 is arg2)
            elif current_opcode == OPCodes.JUMP:
                self.pc = current_argument
                continue
            elif current_opcode == OPCodes.JUMP_IF_TRUE:
                if current_operate_stack.pop() is True:
                    self.pc = current_argument
                    continue
            elif current_opcode == OPCodes.JUMP_IF_FALSE:
                if current_operate_stack.pop() is False:
                    self.pc = current_argument
                    continue
            elif current_opcode == OPCodes.JUMP_IF_NULL:
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
            elif current_opcode == OPCodes.RETURN:
                return_value = current_operate_stack.pop()
                self.pc = current_return_address
                self.call_stack.pop()
                self.call_stack[-1].operate_stack.append(return_value)
                continue
            elif current_opcode == OPCodes.EXIT:
                break
            self.pc += 1
