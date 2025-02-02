EMIT_NEWLINES = True

# These must all be single characters with the exception of COMMENT, which may be a sequence.
#   If RADIX_PT is set to "" or None, only integers will be matched.
COMMENT   = '#'
STR_DELIM = '"'
ESCAPE    = '\\'
GRP_SEPR  = '\''
RADIX_PT  = '.'
MID_WORD = ['-']
END_WORD = ['!', '?', '\'']
NON_WORD = [
  ':', ';', '.', ',', '=', '|', '&', '*', '+', '-', '/', '!', '?', '^',
  '@', '~', '%', '$', '`', '<', '>', '×', '÷', 'λ', 'Σ', 'Π', '_', '\'',
  '(', ')', '[', ']', '{', '}', '\\'
]

#~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~

import re

ws_regex = re.compile(f"\\s+")

grp_sepr = re.escape(GRP_SEPR)
radix_pt = re.escape(RADIX_PT)
if RADIX_PT:
    num_regex = re.compile(f"\\d+({grp_sepr}\\d+)*({radix_pt}\d+({grp_sepr}\\d+)*)?")
else:
    num_regex = re.compile(f"\\d+({grp_sepr}\\d+)*")

def bracket_escape(chars):
    subs = {'\\': '\\\\', ']': '\\]'}
    esc = [subs.get(c, c) for c in chars]
    if esc[0] == '^': esc[0] = '\\^'
    return esc

word = '[^\s' + ''.join(bracket_escape(NON_WORD+[COMMENT,STR_DELIM])) + ']'
mid_word = '[' + ''.join(bracket_escape(MID_WORD)) + ']'
end_word = '(' + '|'.join(re.escape(char)+'+' for char in END_WORD) + ')'

word_regex = re.compile(f"{word}+({mid_word}{word}+)*{end_word}?")

escape_seq = {ESCAPE: ESCAPE, STR_DELIM: STR_DELIM, 'n': '\n', 'r': '\r', 'e': '\x1B'}

#~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~

# The token kinds are "newline", "numeric", "string", "symbol", and "word".
class Token:
    def __init__(self, text, value, kind, line, column):
        self.text   = text
        self.value  = value
        self.kind   = kind
        self.line   = line
        self.column = column

    def __repr__(self):
        tk = "\x1B[38;5;42mToken\x1B[39m"
        if self.value is None:
            return f"{tk} : {self.kind} @ {self.line},{self.column}"
        value = repr(self.value) if self.kind == 'string' else self.value
        return f"{tk} {value} : {self.kind} @ {self.line},{self.column}"


class TokenStream:
    def __init__(self, text, more = None):
        """
        text -- text to be tokenized
        more -- nullary function that will be called to get more text
        """
        self.text   = text
        self.more   = more
        self.line   = 1
        self.column = 1
        self.just_emitted_newline = False
        self.log = text

    def _advance(self, string):
        newlines = string.count("\n")
        if newlines == 0:
            self.column = self.column + len(string)
        else:
            self.line = self.line + newlines
            self.column = len(string) - string.rindex("\n")

    def __next__(self):
        while True:
            # Strip leading whitespace (or emit a newline token)
            match = ws_regex.match(self.text)
            if match is not None:
                tok_line, tok_column = self.line, self.column

                whitespace = match.group()
                self._advance(whitespace)
                self.text = self.text[match.end():]

                if EMIT_NEWLINES and ("\n" in whitespace) and not self.just_emitted_newline:
                    self.just_emitted_newline = True
                    return Token(whitespace, None, 'newline', tok_line, tok_column)

            # Is the text empty?
            if len(self.text) == 0:
                if self.more is None:
                    return None
                addendum = self.more()
                self.text += addendum
                self.log  += addendum
                continue

            # Is this a comment?
            if self.text.startswith(COMMENT):
                while True:
                    if "\n" in self.text:
                        end_of_comment = self.text.index("\n")
                        self._advance(self.text[:end_of_comment])
                        self.text = self.text[end_of_comment:]
                        break
                    else:
                        self._advance(self.text)
                        self.text = ""
                        if self.more is None:
                            return None
                        addendum = self.more()
                        self.text += addendum
                        self.log  += addendum
                continue

            # At this point, we're guaranteed not to return a newline, so
            #   go ahead and preemptively set just_emitted_newline to False.
            self.just_emitted_newline = False
            tok_line, tok_column = self.line, self.column

            # Is this a number?
            match = num_regex.match(self.text)
            if match is not None:
                numstr = match.group()
                self._advance(numstr)
                self.text = self.text[match.end():]

                canonical = numstr.replace(GRP_SEPR, '')
                if RADIX_PT in canonical:
                    num = float(canonical)
                else:
                    num = int(canonical)
                return Token(numstr, num, 'numeric', tok_line, tok_column)

            # Is this a string?
            if self.text.startswith(STR_DELIM):
                idx = 1
                escape = False
                value = []
                while True:
                    if idx >= len(self.text):
                        if self.more is None:
                            raise Exception(f"unterminated string ({tok_line}, {tok_column})")
                        addendum = self.more()
                        self.text += addendum
                        self.log  += addendum
                        continue
                    char = self.text[idx]
                    if escape:
                        replacement = escape_seq.get(char, None)
                        if replacement is None:
                            raise Exception(f"unknown escape sequence ({tok_line}, {tok_column})")
                        else:
                            value.append(replacement)
                        escape = False
                    elif char == ESCAPE:
                        escape = True
                    elif char == STR_DELIM:
                        idx += 1
                        break
                    else:
                        value.append(char)
                    idx += 1
                verbatim = self.text[:idx]
                self._advance(verbatim)
                self.text = self.text[idx:]

                value = ''.join(value)
                return Token(verbatim, value, 'string', tok_line, tok_column)

            # Is this a symbol?
            if self.text[0] in NON_WORD:
                symbol = self.text[0]
                self._advance(symbol)
                self.text = self.text[1:]
                return Token(symbol, symbol, 'symbol', tok_line, tok_column)

            # This must be a word.
            match = word_regex.match(self.text)
            if match is not None:
                word = match.group()
                self._advance(word)
                self.text = self.text[match.end():]
                return Token(word, word, 'word', tok_line, tok_column)

            raise Exception(f"unknown lexing error ({tok_line}, {tok_column})")

    def readline(self):
        buf = []
        while True:
            tok = next(self)
            if tok is None:
                return None if len(buf) == 0 else buf
            if tok.kind == 'newline':
                return buf
            buf.append(tok)


class TokenBuffer:
    def __init__(self, stream, more = None):
        """
        stream -- text or instance of TokenStream
        more   -- nullary function that will be called to get more text
        """
        if isinstance(stream, str):
            self.stream = TokenStream(stream, more)
        else:
            self.stream = stream
        self.buffer = []
        self.is_complete = False

    def __len__(self):
        if self.is_complete:
            return len(self.buffer)
        else:
            raise Exception("length unknown because buffer has not been completed")

    def __getitem__(self, idx):
        if self.is_complete:
            return self.buffer[idx]
        else:
            if idx < 0:
                raise IndexError("length unknown because buffer has not been completed")
            if idx >= len(self.buffer):
                for _ in range(idx - len(self.buffer) + 1):
                    tok = next(self.stream)
                    if tok is None:
                        self.is_complete = True
                        break
                    self.buffer.append(tok)
            return self.buffer[idx]

    def complete(self):
        if self.stream.more is not None:
            raise Exception("cannot complete buffer while self.stream.more is not None")
        while (tok := next(self.stream)) is not None:
            self.buffer.append(tok)
        self.is_complete = True

#~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~

if __name__ == '__main__':

    EMIT_NEWLINES = True

    def prompt():
        print("\x1B[2mlex:\x1B[22m", end=' ')
        line = input()
        if line in ['exit', 'quit']:
            exit()
        return line + "\n"

    stream = TokenStream("", prompt)

    while True:
        print(next(stream))
