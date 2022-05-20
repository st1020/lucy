from ..lucy_data import TableData

from .convert import lib_table as convert_lib_table
from .stdio import lib_table as stdio_lib_table

lib_table = TableData({
    'convert': convert_lib_table,
    'stdio': stdio_lib_table,
})
