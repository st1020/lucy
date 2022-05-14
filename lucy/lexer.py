from enum import Enum
from typing import Any

from .exceptions import LexerError, ErrorCode

escape_sequence = {
    '\\': '\\',
    '\'': '\'',
    '\"': '\"',
    'a': '\a',
    'b': '\b',
    'f': '\f',
    'n': '\n',
    'r': '\r',
    't': '\t',
    'v': '\b'
}


class Location:
    def __init__(self, lineno: int, column: int, offset: int):
        self.lineno = lineno
        self.column = column
        self.offset = offset


class TokenType(Enum):
    # reserved word
    IF = 'if'
    ELSE = 'else'
    LOOP = 'loop'
    WHILE = 'while'
    FOR = 'for'
    IN = 'in'
    BREAK = 'break'
    CONTINUE = 'continue'
    GOTO = 'goto'
    RETURN = 'return'
    GLOBAL = 'global'

    IS = 'is'
    AND = 'and'
    OR = 'or'
    FUNC = 'func'

    NULL = 'null'
    TRUE = 'true'
    FALSE = 'false'

    # symbols
    # single character symbols
    LBRACE = '{'
    RBRACE = '}'

    LBRACKET = '['
    RBRACKET = ']'

    LPAREN = '('
    RPAREN = ')'

    COMMA = ','
    SEMI = ';'
    COLON = ':'
    POINT = '.'
    VBAR = '|'

    ASSIGN = '='

    ADD = '+'
    SUB = '-'
    MUL = '*'
    DIV = '/'
    MOD = '%'

    NOT = '!'
    LESS = '<'
    GREATER = '>'

    # double character symbols
    EQUAL = '=='
    NOT_EQUAL = '!='
    LESS_EQUAL = '<='
    GREATER_EQUAL = '>='

    PLUS_ASSIGN = '+='
    MINUS_ASSIGN = '-='
    MUL_ASSIGN = '*='
    DIV_ASSIGN = '/='
    MOD_ASSIGN = '%='

    # other
    INTEGER = 'INTEGER'
    FLOAT = 'FLOAT'
    STRING = 'STRING'

    ID = 'ID'
    EOF = 'EOF'

    @classmethod
    def exists(cls, item: str) -> bool:
        try:
            dir(cls).index(item)
        except ValueError:
            return False
        else:
            return True

    @classmethod
    def _build_reserved_dict(cls, start, end):
        token_list = list(cls)
        start_index = token_list.index(start)
        end_index = token_list.index(end)
        return {
            token_type.value: token_type
            for token_type in token_list[start_index:end_index + 1]
        }

    @classmethod
    def reserved_word(cls):
        return cls._build_reserved_dict(TokenType.IF, TokenType.FALSE)

    @classmethod
    def single_character_symbols(cls):
        return cls._build_reserved_dict(TokenType.LBRACE, TokenType.GREATER)

    @classmethod
    def double_character_symbols(cls):
        return cls._build_reserved_dict(TokenType.EQUAL, TokenType.MOD_ASSIGN)


class Token:
    def __init__(self, token_type: TokenType, value: Any, start: Location, end: Location):
        self.type = token_type
        self.value = value
        self.start = start
        self.end = end

    def __repr__(self):
        return f'Token({self.type}, {repr(self.value)}, ' \
               f'position={self.start.lineno}:{self.start.column} to {self.end.lineno}:{self.end.column})'


class Lexer:
    def __init__(self, text: str):
        self.text = text
        self.position = 0
        self.current_char = self.text[self.position]
        self.next_char = self.text[self.position + 1]
        self.lineno = 1
        self.column = 1

    def location(self):
        return Location(self.lineno, self.column, self.position)

    def advance_position(self):
        if self.current_char == '\n':
            self.lineno += 1
            self.column = 0
        self.position += 1
        if self.position >= len(self.text):
            self.current_char = None
        else:
            self.current_char = self.text[self.position]
            self.column += 1
            if self.position + 1 >= len(self.text):
                self.next_char = None
            else:
                self.next_char = self.text[self.position + 1]

    def get_next_token(self):
        while self.current_char is not None:
            start = self.location()
            if self.current_char.isspace():
                # 跳过空白
                while self.current_char is not None and self.current_char.isspace():
                    self.advance_position()
                continue
            elif self.current_char == '/' and self.next_char is not None and self.next_char == '/':
                # 跳过注释
                while self.current_char is not None and self.current_char != '\n':
                    self.advance_position()
                self.advance_position()
                continue
            elif self.current_char.isdigit():
                # 处理数字
                value = ''
                while self.current_char is not None and self.current_char.isdigit():
                    value += self.current_char
                    self.advance_position()
                if self.current_char == '.':
                    value += self.current_char
                    self.advance_position()
                    while self.current_char is not None and self.current_char.isdigit():
                        value += self.current_char
                        self.advance_position()
                    return Token(TokenType.FLOAT, float(value), start, self.location())
                else:
                    return Token(TokenType.INTEGER, int(value), start, self.location())
            elif self.current_char.isalpha():
                # 处理字母
                # 处理为关键字或ID
                value = ''
                while self.current_char is not None and (self.current_char.isalnum() or self.current_char == '_'):
                    value += self.current_char
                    self.advance_position()
                token_type = TokenType.reserved_word().get(value)
                if token_type is not None:
                    if token_type == TokenType.NULL:
                        value = None
                    elif token_type == TokenType.TRUE:
                        value = True
                    elif token_type == TokenType.FALSE:
                        value = False
                    return Token(token_type, value, start, self.location())
                else:
                    return Token(TokenType.ID, value, start, self.location())
            elif self.current_char == '\"' or self.current_char == '\'':
                # 处理字符串
                value = ''
                self.advance_position()
                while self.current_char != '\"' and self.current_char != '\'':
                    if self.current_char == '\\':
                        self.advance_position()
                        if self.current_char in escape_sequence.keys():
                            value += escape_sequence[self.current_char]
                        else:
                            value += '\\' + self.current_char
                    else:
                        value += self.current_char
                    self.advance_position()
                self.advance_position()
                return Token(TokenType.STRING, value, start, self.location())
            else:
                # 符号
                if self.next_char is not None:
                    # 双字符符号
                    token_type = TokenType.double_character_symbols().get(self.current_char + self.next_char)
                    if token_type is not None:
                        self.advance_position()
                        self.advance_position()
                        return Token(token_type, token_type.value, start, self.location())
                # 单字符符号
                token_type = TokenType.single_character_symbols().get(self.current_char)
                if token_type is not None:
                    self.advance_position()
                    return Token(token_type, token_type.value, start, self.location())
                else:
                    raise LexerError(
                        error_code=ErrorCode.LEXER_ERROR,
                        message=f"Lexer error on '{self.current_char}' line: {self.lineno} column: {self.column}"
                    )

        return Token(TokenType.EOF, None, Location(1, 1, 0), self.location())
