from lexer import Token

# Arranged from high to low precedence. Unary operators are 'prefix' or 'postfix', and binary
#   operators are 'left' or 'right' associative.
# The None operator is function application; otherwise, operators must be one or two characters
#   long (but not longer).
OPERATORS = [
    ('left',    [('.',   'dot2' ),                                                 ]),
    ('postfix', [('?',   'opt1' ),                                                 ]),
    ('left',    [(None,  'appl2'),                                                 ]),
    ('right',   [('^',   'expo2'),                                                 ]),
    ('prefix',  [('+',   'plus1'), ('-',  'minus1'), ('!', 'not1'),                ]),
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
    ('left',    [(',',   'com2' ),                                                 ]),
    ('right',   [(':=',  'def2' ),                                                 ]),
    ('right',   [('<-',  'assn2'),                                                 ]),
    ('left',    [(';',   'sem2' ),                                                 ]),
]

#~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~

singlechar_ops = []     # [str]
multichar_ops  = []     # [str]

prefix_ops  = {}        # {str -> (precedence : int, name : str)}
postfix_ops = {}        # {str -> (precedence : int, name : str)}
binary_ops  = {}        # {str -> (precedence : int, right-assoc : bool, name : str)}

for prec in range(len(OPERATORS)):
    level = OPERATORS[-1 - prec]
    if level[0] in ('prefix', 'postfix'):
        op_dict = (postfix_ops if level[0] == 'postfix' else prefix_ops)
        for op in level[1]:
            sym, name = op
            op_dict[sym] = (prec, name)
            if sym is None:
                raise Exception("application must be a binary operator")

    elif level[0] in ('left', 'right'):
        rassoc = (level[0] == 'right')
        for op in level[1]:
            sym, name = op
            binary_ops[sym] = (prec, rassoc, name)
    else:
        raise Exception("associativity should be 'left', 'right', 'prefix', or 'postfix'")

    for op in level[1]:
        sym, _ = op
        if sym is None:
            continue
        if len(sym) > 1:
            multichar_ops.append(sym)
        elif len(sym) > 0:
            singlechar_ops.append(sym)

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

#~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~

def _parse_operators(seq, min_precedence):
    """
    Returns a token or ParseTree.
    """
    if len(seq) == 0:
        return 

    lhs = seq[0]
    index = 1
    if isinstance(lhs, Token) and lhs.kind == 'symbol':
        if lhs.value in prefix_ops:
            precedence, name = prefix_ops[lhs.value]
            rhs_parse = _parse_operators(seq[index:], precedence)
            if isinstance(rhs_parse, ParseFailure):
                return rhs_parse
            rhs, num_tokens = rhs_parse
            index += num_tokens
            lhs = ParseTree(name, [rhs])

        elif lhs.value in binary_ops:
            return ParseFailure('binary operator missing left-hand argument', lhs)

    while True:
        if index >= len(seq):
            break

        op = seq[index]
        is_symbol = isinstance(op, Token) and op.kind == 'symbol'
        if is_symbol and op.value in postfix_ops:
            precedence, name = postfix_ops[op.value]
            if precedence < min_precedence:
                break
            lhs = ParseTree(name, [lhs])
            index += 1
            continue

        elif is_symbol and op.value in binary_ops:
            precedence, rassoc, name = binary_ops[op.value]
            if precedence < min_precedence:
                break
            index += 1
            if index >= len(seq):
                return ParseFailure('binary operator missing right-hand argument', op)

        else:
            precedence, rassoc, name = binary_ops[None]
            if precedence < min_precedence:
                break

        rhs_parse = _parse_operators(seq[index:], precedence + (0 if rassoc else 1))
        if isinstance(rhs_parse, ParseFailure):
            return rhs_parse
        rhs, num_tokens = rhs_parse

        index += num_tokens
        lhs = ParseTree(name, [lhs, rhs])

    return (lhs, index)


def parse_operators(seq):
    parse = _parse_operators(seq, 0)
    if isinstance(parse, ParseFailure):
        return parse
    return parse[0]


def parse_interior(container, seq):
    """
    Returns a list of tokens and/or ParseTrees.

    container -- the context in which seq appears ('root', 'parentheses', 'brackets', or 'braces')
    seq       -- a list of tokens and/or ParseTrees guaranteed to not include any delimiters
    """
    op_parse = parse_operators(seq)
    if isinstance(op_parse, ParseFailure):
        return op_parse
    if container == 'brackets' or container == 'braces':
        return [ParseTree(container, [op_parse])]
    return [op_parse]


def adjacent(tok1, tok2):
    return tok2.line == tok1.line and abs(tok2.column - tok1.column) == 1


def parse(seq):
    # Join up multicharacter operators
    if len(multichar_ops) > 0:
        index = 0
        while index < len(seq)-1:
            if (tok1 := seq[index]).kind == 'symbol' and (tok2 := seq[index+1]).kind == 'symbol':
                if adjacent(tok1, tok2) and (concat := tok1.value + tok2.value) in multichar_ops:
                    tok = Token(concat, concat, 'symbol', tok1.line, tok1.column)
                    seq[index] = tok
                    seq[index+1] = None
                    index += 1
            index += 1

        seq = [tok for tok in seq if tok is not None]

    # Handle delimiters (parentheses, brackets, and braces)
    left_delims   = ('(', '[', '{')
    right_delims  = (')', ']', '}')
    corresponding = {'(': ')', '[': ']', '{': '}'}
    delim_name    = {')': 'parentheses', ']': 'brackets', '}': 'braces'}

    stack = []
    index = 0
    while True:
        if index >= len(seq):
            break

        token = seq[index]
        if token.kind != 'symbol' or token.value not in (left_delims+right_delims):
            index += 1
            continue

        if token.value in left_delims:
            stack.append((index, corresponding[token.value]))
            index += 1
            continue

        if len(stack) == 0:
            return ParseFailure('unpaired delimiter', token)

        left_index, expected_delim = stack[-1]
        if token.value != expected_delim:
            return ParseFailure('mismatched or unpaired delimiter', token)

        interior = seq[left_index+1:index]
        inter_length = len(interior)

        replacement = parse_interior(delim_name[token.value], interior)
        if isinstance(replacement, ParseFailure):
            return replacement
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
