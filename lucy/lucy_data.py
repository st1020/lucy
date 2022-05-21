from typing import Dict, Union, Optional, Callable

from .codegen import Function


class GlobalReference:
    obj = None

    def __new__(cls, *args, **kwargs):
        if cls.obj is None:
            cls.obj = super().__new__(cls)
        return cls.obj


class ExtendFunction(Function):
    def __init__(self, params_num: int, func: Callable):
        super().__init__(params_num)
        self.is_closure = False
        self.func = func

    def __repr__(self):
        return f'ExtendFunction({self.func!r})'


NullData = type(None)
BooleanData = bool
IntegerData = int
FloatData = float
StringData = str


class TableData(Dict['T_Data', 'T_Data']):
    def raw_get(self, key):
        try:
            return super().__getitem__(key)
        except KeyError:
            return NullData()

    def __getitem__(self, key):
        table = self
        while not isinstance(table, NullData):
            item = table.raw_get(key)
            if not isinstance(item, NullData):
                return item
            table = table.raw_get('__base__')
            if not isinstance(table, TableData):
                break
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
    def __init__(self,
                 function: Optional[Function],
                 module_id: int = 0,
                 base_closure: Optional['ClosureData'] = None,
                 global_closure: Optional['ClosureData'] = None):
        self.function: Optional[Function] = function
        self.module_id: int = module_id
        self.base_closure: Optional[ClosureData] = base_closure
        self.global_closure: Optional[ClosureData] = global_closure
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
