from ..lucy_data import ClosureData, ExtendFunction, TableData, NullData, T_Data


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


def table_raw_len(table: TableData):
    return len(table)


def table_raw_get(table: TableData, key: T_Data):
    return table[key]


def table_raw_set(table: TableData, key: T_Data, value: T_Data):
    table[key] = value


lib_table = TableData({
    'keys': ClosureData(function=ExtendFunction(func=table_keys, params_num=1)),
    'values': ClosureData(function=ExtendFunction(func=table_values, params_num=1)),
    'raw_len': ClosureData(function=ExtendFunction(func=table_raw_len, params_num=1)),
    'raw_get': ClosureData(function=ExtendFunction(func=table_raw_get, params_num=2)),
    'raw_set': ClosureData(function=ExtendFunction(func=table_raw_set, params_num=3)),
})
