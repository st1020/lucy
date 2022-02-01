from lucy import Lexer, Parser, CodeGenerator, LVM, dump_code, load_code

# 词法解析 -> 语法解析 -> 代码生成 -> 虚拟机
# lexer -> parser -> codegen -> lvm

if __name__ == '__main__':
    code = r'''
    func test_func() {
    }
    test_1 = true;
    test_1 = {'a': 1, "b": {1, 2}};
    test_1.a = 2;
    test_2 = {1, 2, 3};
    func main(a, b) {
        global t;
        a = 0;
        a = a + 1;
        t = {"a": a + 110, "b": 2};
        return 1 + 1;
    }
    a = 0;
    while (a != 10) {
        a = a + 1;
        if (a == 4) {
            d = "123";
            c = null;
            f = false;
            if (!f) {
                e = true;
                break;
            }
        } else {
            d = 1;
        }
    }
    re = main(1, 2);
    lll = {};
    for (k, v in t) {
        lll[v] = k;
    }
    '''
    lex = Lexer(code)
    par = Parser(lex)
    ast = par.parse()
    code = CodeGenerator(ast)
    code_program = code.generate()
    code_program_dict = dump_code(code_program)
    code_program = load_code(code_program_dict)
    lvm = LVM(code_program)
    lvm.run()
    pass
