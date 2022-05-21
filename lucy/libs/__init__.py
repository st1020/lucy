from ..lucy_data import TableData

from .convert import lib_table as convert_lib_table
from .io import lib_table as io_lib_table
from .table import lib_table as table_lib_table

lib_table = TableData({
    'convert': convert_lib_table,
    'io': io_lib_table,
    'table': table_lib_table,
})
