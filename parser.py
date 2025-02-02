from lexer import Token

KEYWORDS = [
]

# Arranged from high to low precedence. Unary operators are 'prefix' or 'postfix', and binary
#   operators are 'left' or 'right' associative.
OPERATORS = [
    ('left',    [('.',   'dot2' ),                                                 ]),
    ('prefix',  [('+',   'plus1'), ('-',  'minus1'), ('!', 'not1'),                ]),
    ('postfix', [('?',   'opt1' ),                                                 ]),
    ('left',    [(None,  'appl2'),                                                 ]),
    ('right',   [('^',   'expo2'),                                                 ]),
    ('left',    [('*',   'mul2' ), ('/',  'div2'  ), ('%', 'mod2'),                ]),
    ('left',    [('+',   'plus2'), ('-',  'minus2'),                               ]),
    ('left',    [('&',   'and2' ),                                                 ]),
    ('left',    [('|',   'or2'  ), ('~',  'xor2'  ),                               ]),
    ('right',   [('++',  'cat2' ), ('::', 'cons2' ),                               ]),
    ('left',    [('>=',  'geq2' ), ('<=', 'leq2'  ), ('>',  'gt2' ), ('<', 'lt2'), ]),
    ('left',    [('=',   'eq2'  ), ('==', 'deq2'  ), ('!=', 'neq2'),               ]),
    ('right',   [('&&',  'land2'),                                                 ]),
    ('right',   [('||',  'lor2' ),                                                 ]),
    ('right',   [('$',   'seq2' ),                                                 ]),
    ('left',    [(':',   'typ2' ),                                                 ]),
    ('right',   [(':=',  'def2' ),                                                 ]),
    ('right',   [('<-',  'assn2'),                                                 ]),
    ('left',    [(',',   'com2' ),                                                 ]),
    ('left',    [(';',   'sem2' ),                                                 ]),
]

#~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~

class ParseTree:
    def __init__(self, label, children):
        self.label = label
        self.children = children

    def __repr__(self):
        tr = "\x1B[38;5;129mTree\x1B[39m"
        return f"{tr} {self.label}"

    def __len__(self):
        return len(self.children)

    def __iter__(self):
        return iter(self.children)

    def __getitem__(self, x):
        return self.children[x]

    def show(self, indent=0):
        margin = "\x1B[2m\u2502\x1B[22m "
        print(margin*indent, end='')
        print(self)
        for child in self.children:
            if isinstance(child, Token):
                print(margin*(indent+1), end='')
                print(child)
            else:
                child.show(indent+1)


def extract_tokens(obj):
    if isinstance(obj, Token):
        return [obj]
    if isinstance(obj, ParseTree):
        return sum((extract_tokens(x) for x in obj.children), [])
    raise RuntimeError(f"unable to extract tokens from {type(obj)}")


class ParseFailure:
    def __init__(self, msg, hi):
        """
        msg -- string describing the failure
        hi  -- token or parse tree
        """
        self.message = msg
        self.labels = []
        self.highlight = hi

    def __repr__(self):
        return f"\x1B[91merror\x1B[39m: {self.message}"

    def mark(self, label):
        self.labels.append(label)

    def show(self, log_lines):
        """
        log_lines -- a copy of the text prior to tokenization split into lines
        """
        if self.highlight is None:
            print(f"\x1B[91merror\x1B[39m: {self.message}")
            return
        tokens = extract_tokens(self.highlight)
        top = tokens[ 0].line - 1
        bot = tokens[-1].line - 1
        if bot-top > 1:
            return  # not sure yet how to display multi-line errors
        print(f"\x1B[91merror\x1B[39m: line {tokens[0].line}: " + self.message)
        labels = [x for x in self.labels if x is not None][::-1]
        line = log_lines[top]
        margin = "\x1B[2m\u2502\x1B[22m "
        if len(labels) > 0:
            print(margin, end='')
            print(f"\x1B[2min {'/'.join(labels)}")
        print(margin)
        print(margin + line)
        print(margin, end='')
        left  = tokens[ 0].column - 1
        right = tokens[-1].column - 1 + len(tokens[-1].text)

        print(" "*left, end='')
        print("\x1B[91m^", end='')
        print("~"*(right-left-1), end='')
        print("\x1B[39m", end='')
        print()


def adjacent(tok1, tok2):
    return tok2.line == tok1.line and abs(tok2.column - tok1.column) == 1


def parse_operators(seq, min_precedence):
    pass


def parse_interior(container, seq):
    """
    seq -- a list of tokens and ParseTrees guaranteed to not include any delimiters
    """
    return [ParseTree(container, seq)]


def parse(seq):
    left_delims  = ('(', '[', '{')
    right_delims = (')', ']', '}')
    delims = ('(', ')', '[', ']', '{', '}')
    dual   = {'(': ')', '[': ']', '{': '}'}
    d_name = {')': 'parentheses', ']': 'brackets', '}': 'braces'}


    # Handle delimiters (parentheses, brackets, and braces)
    stack = []
    index = 0
    while True:
        if index >= len(seq):
            break

        token = seq[index]
        if token.kind != 'symbol' or token.value not in delims:
            index += 1
            continue

        if token.value in left_delims:
            stack.append((index, dual[token.value]))
            index += 1
            continue

        if len(stack) == 0:
            return ParseFailure('unpaired delimiter', token)

        left_index, expected_delim = stack[-1]
        if token.value != expected_delim:
            return ParseFailure('mismatched or unpaired delimiter', token)

        interior = seq[left_index+1:index]
        inter_length = len(interior)

        replacement = parse_interior(d_name[token.value], interior)
        repl_length = len(replacement)

        seq = seq[:left_index] + replacement + seq[index+1:]
        index = index - 1 - (inter_length - repl_length) - 1

        stack.pop()
        index += 1

    if len(stack) > 0:
        left_index, _ = stack[-1]
        return ParseFailure('unpaired delimiter', seq[left_index])

    # Parse the delimiter-free sequence
    return parse_interior('root', seq)


#~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~

if __name__ == '__main__':

    from lexer import TokenStream

    EMIT_NEWLINES = True

    def prompt():
        print("\x1B[2mparse:\x1B[22m", end=' ')
        line = input()
        if line in ['exit', 'quit']:
            exit()
        return line + "\n"

    stream = TokenStream("", prompt)

    while True:
        result = parse(stream.readline())
        if isinstance(result, ParseFailure):
            log_lines = stream.log.split('\n')
            result.show(log_lines)
        else:
            for obj in result:
                obj.show()
