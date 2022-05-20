from ..lucy_data import ClosureData, ExtendFunction, TableData

lib_table = TableData({
    'print': ClosureData(function=ExtendFunction(func=lambda x: print(x, end=''), params_num=1)),
    'println': ClosureData(function=ExtendFunction(func=print, params_num=1)),
    'input': ClosureData(function=ExtendFunction(func=input, params_num=0)),
})
