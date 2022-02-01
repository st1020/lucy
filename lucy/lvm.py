from collections import defaultdict
from typing import Any, List, Dict, Union

from .exceptions import LVMError, ErrorCode
from .codegen import Code, CodeProgram, OPCodes, Function, T_LITERAL


class GlobalReference:
    # 表示向全局变量的引用
    pass


class ExtendFunction(Function):
    def __init__(self, params_num: int, extend_argument: str):
        super().__init__(params_num)
        self.extend_argument: str = extend_argument

    def __repr__(self):
        return f'extend_function({self.extend_argument!r})'


T_VARIABLE = Union[T_LITERAL, Dict[str, Any], GlobalReference]
GlobalReferenceObject = GlobalReference()


class StackFrame:
    def __init__(self,
                 operate_stack: List[T_VARIABLE] = None,
                 variables: Dict[int, T_VARIABLE] = None,
                 return_address: int = 0):
        if operate_stack is None:
            operate_stack = list()
        if variables is None:
            variables = defaultdict(lambda: None)
        self.operate_stack: List[T_VARIABLE] = operate_stack
        self.variables: Dict[int, T_VARIABLE] = variables
        self.return_address: int = return_address


class LVM:
    version = '0.1.0'

    def __init__(self, code_program: CodeProgram):
        self.code_program: CodeProgram = code_program
        self.code_list = self.code_program.code_list
        self.literal_list = self.code_program.literal_list
        self.pc: int = 0
        self.global_stack_frame: StackFrame = StackFrame()
        self.call_stack: List[StackFrame] = [self.global_stack_frame]

    def run(self):
        def check_table_index(value):
            if isinstance(value, str):
                return value
            elif isinstance(value, int) or isinstance(value, float):
                return str(value)
            else:
                raise TypeError('table index must be string or number')

        try:
            while self.pc < len(self.code_list):
                current_code: Code = self.code_list[self.pc]
                current_operate_stack = self.call_stack[-1].operate_stack
                current_variables = self.call_stack[-1].variables
                current_return_address = self.call_stack[-1].return_address
                current_argument = current_code.argument

                if current_code.opcode == OPCodes.PUSH_LITERAL:
                    current_operate_stack.append(self.literal_list[current_argument])
                elif current_code.opcode == OPCodes.PUSH:
                    target = current_variables[current_argument]
                    if isinstance(target, GlobalReference) or target is None:
                        target = self.global_stack_frame.variables[current_argument]
                    current_operate_stack.append(target)
                elif current_code.opcode == OPCodes.TOP:
                    if isinstance(current_variables[current_argument], GlobalReference):
                        if current_operate_stack[-1] is None:
                            self.global_stack_frame.variables.pop(current_argument)
                        else:
                            self.global_stack_frame.variables[current_argument] = current_operate_stack[-1]
                    else:
                        if current_operate_stack[-1] is None:
                            if current_argument in current_variables.keys():
                                current_variables.pop(current_argument)
                        else:
                            current_variables[current_argument] = current_operate_stack[-1]
                elif current_code.opcode == OPCodes.POP:
                    current_operate_stack.pop()
                elif current_code.opcode == OPCodes.GLO:
                    current_variables[current_argument] = GlobalReferenceObject
                elif current_code.opcode == OPCodes.NEW_TABLE:
                    current_operate_stack.append(defaultdict(lambda: None))
                elif current_code.opcode == OPCodes.GET_TABLE_TOP:
                    arg2 = current_operate_stack.pop()
                    arg1 = current_operate_stack[-1]
                    current_operate_stack.append(arg1[check_table_index(arg2)])
                elif current_code.opcode == OPCodes.SET_TABLE_TOP:
                    arg3 = current_operate_stack.pop()
                    arg2 = current_operate_stack.pop()
                    arg1 = current_operate_stack[-1]
                    arg1[check_table_index(arg2)] = arg3
                elif current_code.opcode == OPCodes.FOR:
                    temp = current_operate_stack.pop()
                    current_operate_stack.append(0)
                    current_operate_stack.append(temp)
                elif current_code.opcode == OPCodes.FOR_PRE:
                    if current_operate_stack[-2] < len(current_operate_stack[-1]):
                        key = list(current_operate_stack[-1].keys())[current_operate_stack[-2]]
                    else:
                        key = None
                    current_operate_stack[-2] += 1
                    current_operate_stack.append(key)
                elif current_code.opcode == OPCodes.NEG:
                    current_operate_stack.append(-current_operate_stack.pop())
                elif current_code.opcode == OPCodes.NOT:
                    current_operate_stack.append(not current_operate_stack.pop())
                elif current_code.opcode == OPCodes.ADD:
                    arg2 = current_operate_stack.pop()
                    arg1 = current_operate_stack.pop()
                    current_operate_stack.append(arg1 + arg2)
                elif current_code.opcode == OPCodes.SUB:
                    arg2 = current_operate_stack.pop()
                    arg1 = current_operate_stack.pop()
                    current_operate_stack.append(arg1 - arg2)
                elif current_code.opcode == OPCodes.MUL:
                    arg2 = current_operate_stack.pop()
                    arg1 = current_operate_stack.pop()
                    current_operate_stack.append(arg1 * arg2)
                elif current_code.opcode == OPCodes.DIV:
                    arg2 = current_operate_stack.pop()
                    arg1 = current_operate_stack.pop()
                    current_operate_stack.append(arg1 / arg2)
                elif current_code.opcode == OPCodes.MOD:
                    arg2 = current_operate_stack.pop()
                    arg1 = current_operate_stack.pop()
                    current_operate_stack.append(arg1 % arg2)
                elif current_code.opcode == OPCodes.AND:
                    arg2 = current_operate_stack.pop()
                    arg1 = current_operate_stack.pop()
                    current_operate_stack.append(arg1 and arg2)
                elif current_code.opcode == OPCodes.OR:
                    arg2 = current_operate_stack.pop()
                    arg1 = current_operate_stack.pop()
                    current_operate_stack.append(arg1 or arg2)
                elif current_code.opcode == OPCodes.EQ:
                    arg2 = current_operate_stack.pop()
                    arg1 = current_operate_stack.pop()
                    current_operate_stack.append(arg1 == arg2)
                elif current_code.opcode == OPCodes.NE:
                    arg2 = current_operate_stack.pop()
                    arg1 = current_operate_stack.pop()
                    current_operate_stack.append(arg1 != arg2)
                elif current_code.opcode == OPCodes.LT:
                    arg2 = current_operate_stack.pop()
                    arg1 = current_operate_stack.pop()
                    current_operate_stack.append(arg1 < arg2)
                elif current_code.opcode == OPCodes.LE:
                    arg2 = current_operate_stack.pop()
                    arg1 = current_operate_stack.pop()
                    current_operate_stack.append(arg1 <= arg2)
                elif current_code.opcode == OPCodes.GT:
                    arg2 = current_operate_stack.pop()
                    arg1 = current_operate_stack.pop()
                    current_operate_stack.append(arg1 > arg2)
                elif current_code.opcode == OPCodes.GE:
                    arg2 = current_operate_stack.pop()
                    arg1 = current_operate_stack.pop()
                    current_operate_stack.append(arg1 >= arg2)
                elif current_code.opcode == OPCodes.JMP:
                    self.pc = current_argument
                    continue
                elif current_code.opcode == OPCodes.JT:
                    if current_operate_stack.pop() is True:
                        self.pc = current_argument
                        continue
                elif current_code.opcode == OPCodes.JF:
                    if current_operate_stack.pop() is False:
                        self.pc = current_argument
                        continue
                elif current_code.opcode == OPCodes.JNT:
                    if current_operate_stack[-1] is None:
                        self.pc = current_argument
                        continue
                elif current_code.opcode == OPCodes.CALL:
                    self.call_stack.append(StackFrame(
                        operate_stack=[current_operate_stack.pop() for _ in range(current_argument)],
                        return_address=self.pc + 1)
                    )
                    self.pc = current_operate_stack.pop().address
                    continue
                elif current_code.opcode == OPCodes.GOTO:
                    self.call_stack.pop()
                    self.call_stack.append(StackFrame(
                        operate_stack=[current_operate_stack.pop() for _ in range(current_argument)],
                        return_address=current_return_address)
                    )
                    self.pc = current_operate_stack.pop().address
                    continue
                elif current_code.opcode == OPCodes.RET:
                    return_value = current_operate_stack.pop()
                    self.pc = current_return_address
                    self.call_stack.pop()
                    self.call_stack[-1].operate_stack.append(return_value)
                    continue
                elif current_code.opcode == OPCodes.EXIT:
                    break
                self.pc += 1
        except Exception as e:
            raise LVMError(error_code=ErrorCode.LVM_ERROR, message=repr(e))
