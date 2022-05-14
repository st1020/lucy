from lucy import Lexer, Parser, CodeGenerator, LVM

# 词法解析 -> 语法解析 -> 代码生成 -> 虚拟机
# lexer -> parser -> codegen -> lvm


if __name__ == '__main__':
    code = r'''
    a = func () {
        t = 0;
        return || {
            t = t + 1;
            if t > 100 {
                return null;
            }
            return t * 2;
        };
    };
    l = {};
    for i in a() {
        l[i] = i;
    }
    '''
    lex = Lexer(code)
    par = Parser(lex)
    ast = par.parse()
    code = CodeGenerator(ast)
    code_program = code.generate()
    lvm = LVM(code_program)
    lvm.run()
    pass
