from typing import Dict, Union

from .codegen import OPCodes, Code, CodeProgram, Function
from .lvm import T_VARIABLE, GlobalReference, GlobalReferenceObject, ExtendFunction

opcode_name_to_opcodes = {
    opcode.value.name: opcode
    for opcode in OPCodes
}


def dump_data(data: T_VARIABLE):
    if isinstance(data, Function):
        if isinstance(data, ExtendFunction):
            return ['function', {
                'params_num': data.params_num,
                'address': None,
                'extend': True,
                'extend_argument': data.extend_argument
            }]
        return ['function', {
            'params_num': data.params_num,
            'address': data.address,
            'extend': False,
            'extend_argument': None
        }]
    elif isinstance(data, GlobalReference):
        return ['global_reference', {}]
    elif isinstance(data, dict):
        return {
            str(key): dump_data(value)
            for key, value in data.items()
        }
    else:
        return data


def dump_code(code_program: CodeProgram):
    return {
        'code_list': list(map(lambda x: [x.opcode.value.name, x.argument], code_program.code_list)),
        'literal_list': list(map(dump_data, code_program.literal_list))
    }


def load_data(dumped_data: Union[None, bool, int, float, str, dict, list]):
    if isinstance(dumped_data, list):
        if dumped_data[0] == 'function':
            if dumped_data[1]['extend']:
                return ExtendFunction(dumped_data[1]['params_num'], dumped_data[1]['extend_argument'])
            else:
                return Function(dumped_data[1]['params_num'], dumped_data[1]['address'])
        elif dumped_data[0] == 'global_reference':
            return GlobalReferenceObject
    elif isinstance(dumped_data, dict):
        return {
            key: load_data(value)
            for key, value in dumped_data.items()
        }
    else:
        return dumped_data


def load_code(dumped_code: Dict[str, list]):
    return CodeProgram(
        code_list=list(map(lambda x: Code(opcode_name_to_opcodes[x[0]], x[1]), dumped_code['code_list'])),
        literal_list=list(map(load_data, dumped_code['literal_list']))
    )
