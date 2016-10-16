import copy
import re


TEXT = 0x01
COLOR = 0x03
BOLD = 0x02
ITALIC = 0x1d
UNDERLINE = 0x1f
REVERSE = 0x16
RESET = 0x0f


def to_hex_re(num):
    return "\\x{0:02x}".format(num)


# Formatting codes
token_defs = {
    COLOR: r"(\x03((?P<text_color>\d{1,2})(,(?P<bg_color>\d{1,2}))?)?)",
    BOLD: to_hex_re(BOLD),
    ITALIC: to_hex_re(ITALIC),
    UNDERLINE: to_hex_re(UNDERLINE),
    REVERSE: to_hex_re(REVERSE),
    RESET: to_hex_re(RESET),
}

# Everything else is text
token_defs[TEXT] = "(?P<text>[^{0}]+)".format("".join(map(to_hex_re, token_defs.keys())))


class Block(object):
    text_color = 1
    bg_color = 0
    bold = False
    italic = False
    underline = False

    def __init__(self, text=""):
        self.text = text

    def __eq__(self, other):
        return repr(self) == repr(other)

    def __repr__(self):
        return "Block(text_color={0}, bg_color={1}, bold={2}, italic={3}, underline={4}, text=\"{5}\")".format(
            self.text_color, self.bg_color, self.bold, self.italic, self.underline, self.text)


# Tokenize a line of IRC text, making a stream of control codes and raw text
def tokenize(line):
    tokens = []

    while line:
        for token_type, token_re in token_defs.iteritems():
            match = re.match(token_re, line)
            if match:
                tokens.append((token_type, match.groupdict()))
                line = line[match.end():]

    return tokens


# Convert a list of tokens into 'blocks' of text based on chunks of visible output
def blockize(tokens):
    blocks = [Block()]

    for token_type, match in tokens:
        block = blocks[-1]

        if token_type == TEXT:
            block.text += match["text"]
            continue

        elif blocks[-1].text:
            block = copy.copy(block)
            block.text = ""
            blocks.append(block)

        if token_type == BOLD:
            block.bold = not block.bold

        elif token_type == ITALIC:
            block.italic = not block.italic

        elif token_type == UNDERLINE:
            block.underline = not block.underline

        elif token_type == COLOR:
            # Reset to default colors
            if not match["text_color"] and not match["bg_color"]:
                block.text_color = Block.text_color
                block.bg_color = Block.bg_color
            if match["text_color"]:
                block.text_color = int(match["text_color"])
            if match["bg_color"]:
                block.bg_color = int(match["bg_color"])

        elif token_type == REVERSE:
            block.text_color, block.bg_color = block.bg_color, block.text_color

        elif token_type == RESET:
            block = Block(text=block.text)
            blocks[-1] = block

    blocks = filter(lambda b: b.text, blocks)
    return blocks


def stringize(blocks):
    output = ""

    for offset, block in enumerate(blocks):
        if offset:
            prev_block = blocks[offset - 1]
        else:
            prev_block = Block()

        if (block.text_color, block.bg_color) != (prev_block.text_color, prev_block.bg_color):
            output += "\x03{0}".format(block.text_color)
            if block.bg_color != prev_block.bg_color:
                output += ",{0}".format(block.bg_color)

        if block.bold != prev_block.bold:
            output += chr(BOLD)

        if block.italic != prev_block.italic:
            output += chr(ITALIC)

        if block.underline != prev_block.underline:
            output += chr(UNDERLINE)

        output += block.text

    return output

