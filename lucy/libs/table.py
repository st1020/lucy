from ..lucy_data import ClosureData, ExtendFunction, TableData, NullData


def table_keys(table: TableData):
    def keys():
        for i in table.keys():
            yield i
        yield NullData()

    item = keys()
    return ClosureData(function=ExtendFunction(func=lambda: next(item), params_num=0))


def table_values(table: TableData):
    def values():
        for i in table.values():
            yield i
        yield NullData()

    item = values()
    return ClosureData(function=ExtendFunction(func=lambda: next(item), params_num=0))


lib_table = TableData({
    'keys': ClosureData(function=ExtendFunction(func=table_keys, params_num=1)),
    'values': ClosureData(function=ExtendFunction(func=table_values, params_num=1)),
})
