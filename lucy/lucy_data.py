from typing import Dict, Union, Optional, Callable

from .codegen import Function


class ExtendFunction(Function):
    def __init__(self, params_num: int, func: Callable):
        super().__init__(params_num)
        self.is_closure = Function
        self.func = func

    def __repr__(self):
        return f'ExtendFunction({self.func!r})'


NullData = type(None)
BooleanData = bool
IntegerData = int
FloatData = float
StringData = str


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

    def get(self, key: 'T_Data') -> 'T_Data':
        table = self
        while not isinstance(table, NullData):
            item = table[key]
            if not isinstance(item, NullData):
                return item
            table = table['__base__']
            if not isinstance(table, TableData):
                break
        return NullData()

    def row_get(self, key: 'T_Data') -> 'T_Data':
        return self[key]


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

    def __repr__(self):
        return repr(self.function)


T_Data = Union[NullData, BooleanData, IntegerData, FloatData, StringData, TableData, ClosureData]
HASHABLE_DATA_TYPE = (NullData, BooleanData, IntegerData, FloatData, StringData)
LUCY_DATA_TYPE = HASHABLE_DATA_TYPE + (TableData, ClosureData)
