from ..lucy_data import ClosureData, ExtendFunction, TableData

lib_table = TableData({
    'bool': ClosureData(function=ExtendFunction(func=bool, params_num=1)),
    'int': ClosureData(function=ExtendFunction(func=int, params_num=1)),
    'float': ClosureData(function=ExtendFunction(func=float, params_num=1)),
    'string': ClosureData(function=ExtendFunction(func=str, params_num=1)),
})
