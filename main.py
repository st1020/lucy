from lucy import LVM

# 词法解析 -> 语法解析 -> 代码生成 -> 虚拟机
# lexer -> parser -> codegen -> lvm


if __name__ == '__main__':
    LVM.run_file('tests/test1.lucy')
