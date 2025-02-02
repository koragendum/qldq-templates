from lexer import Token

INFINITY = 1024

# A parser is a lambda that takes a list of tokens and returns a tuple (remaining, parse tree)
#   or a ParseFailure.
# A parse tree is a list of the form [label, subtree, subtree, ...].

def extract_tokens(obj):
    if isinstance(obj, Token):
        return [obj]
    out = []
    for x in obj[1:]:
        out += extract_tokens(x)
    return out

class ParseFailure:
    def __init__(self, msg, label, hi):
        """
        msg -- string describing the failure
        hi  -- parse tree
        """
        self.message = msg
        self.labels = [label]
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

def Seq(*parsers, label=None):
    def composition(tokens):
        remaining = tokens
        tree = [label]
        for p in parsers:
            result = p(remaining)
            if isinstance(result, ParseFailure):
                result.mark(label)
                return result
            remaining, subtree = result
            if subtree[0] is None:
                tree += subtree[1:]
            else:
                tree.append(subtree)
        return (remaining, tree)

    return composition

def Rep(parser, minim: 0, maxim: INFINITY, label: None):
    pass

def Opt(*parsers, label: None):
    pass

def Literal(kind, value, label=None):
    def matcher(tokens):
        if len(tokens) == 0:
            return ParseFailure(f"unexpectedly reached end of text", label, None)
        tok = tokens[0]

        if isinstance(kind, str):
            kind_match = tok.kind == kind
        elif isinstance(kind, tuple) or isinstance(kind, list):
            kind_match = tok.kind in kind
        else:
            kind_match = True

        if isinstance(value, str):
            value_match = tok.value == value
        elif isinstance(value, tuple) or isinstance(value, list):
            value_match = tok.value in value
        else:
            value_match = True

        tree = [label, tok]
        if kind_match and value_match:
            return (tokens[1:], tree)
        else:
            if not kind_match:
                if isinstance(kind, tuple) or isinstance(kind, list):
                    msg = f"expected one of {kind}"
                else:
                    msg = f"expected {kind}"
            if not value_match:
                if isinstance(value, tuple) or isinstance(value, list):
                    msg = f"expected one of {value}"
                else:
                    msg = f"expected {value}"
            return ParseFailure(msg, label, tree)

    return matcher

def Symbol(value, label=None):
    return Literal('symbol', value, label)

def Keyword(value, label=None):
    return Literal('word', value, label)

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

    parser = Seq(Symbol('('), Seq(Symbol('*', label='sym')), Symbol(')'), label='test')
    stream = TokenStream("", prompt)

    while True:
        result = parser(stream.readline())
        if isinstance(result, ParseFailure):
            result.show(stream.log.split('\n'))
        else:
            remaining, tokens = result
            print(tokens)
