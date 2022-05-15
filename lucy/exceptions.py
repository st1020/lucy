from enum import Enum


class ErrorCode(Enum):
    # LexerError
    LEXER_ERROR = 'Lexer Error'

    # ParseError
    UNEXPECTED_TOKEN = 'Unexpected token'
    ASSIGNING_TO_RVALUE = 'Assigning to rvalue'
    GOTO_UNEXPECTED_EXPRESSION = 'Goto unexpected expression'

    # CodeGeneratorError
    UNEXPECTED_AST_NODE = 'Unexpected ast node'
    UNSYNTACTIC_BREAK = 'Unsyntactic break'
    UNSYNTACTIC_CONTINUE = 'Unsyntactic continue'

    # LVMError
    TYPE_ERROR = 'Type Error'
    CALL_ERROR = 'Call Error'
    EXTEND_FUNCTION_ERROR = 'Extend Function Error'


class InterpreterError(Exception):
    def __init__(self, error_code: ErrorCode, message: str = ''):
        # 在message前添加异常类名
        super().__init__(f'{self.__class__.__name__}: {error_code.value}: {message}')


class LexerError(InterpreterError):
    pass


class ParserError(InterpreterError):
    pass


class CodeGeneratorError(InterpreterError):
    pass


class LVMError(InterpreterError):
    pass
