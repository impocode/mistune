import re
from .scanner import ScannerParser, Matcher

_LINE_BREAK = re.compile(r'\n{2,}')

_BLOCK_QUOTE_LEADING = re.compile(r'^ *> ?', flags=re.M)
_BLOCK_TAGS = {
    'address', 'article', 'aside', 'base', 'basefont', 'blockquote',
    'body', 'caption', 'center', 'col', 'colgroup', 'dd', 'details',
    'dialog', 'dir', 'div', 'dl', 'dt', 'fieldset', 'figcaption',
    'figure', 'footer', 'form', 'frame', 'frameset', 'h1', 'h2', 'h3',
    'h4', 'h5', 'h6', 'head', 'header', 'hr', 'html', 'iframe',
    'legend', 'li', 'link', 'main', 'menu', 'menuitem', 'meta', 'nav',
    'noframes', 'ol', 'optgroup', 'option', 'p', 'param', 'section',
    'source', 'summary', 'table', 'tbody', 'td', 'tfoot', 'th', 'thead',
    'title', 'tr', 'track', 'ul'
}
_BLOCK_HTML_RULE6 = (
    r'</?(?:' + '|'.join(_BLOCK_TAGS) + r')'
    r'(?: +|\n|/?>)[\s\S]*?'
    r'(?:\n{2,}|\n*$)'
)
_BLOCK_HTML_RULE7 = (
    # open tag
    r'<(?!script|pre|style)([a-z][\w-]*)(?:'
    r' +[a-zA-Z:_][\w.:-]*(?: *= *"[^"\n]*"|'
    r''' *= *'[^'\n]*'| *= *[^\s"'=<>`]+)?'''
    r')*? */?>(?=\s*\n)[\s\S]*?(?:\n{2,}|\n*$)|'
    # close tag
    r'</(?!script|pre|style)[a-z][\w-]*\s*>(?=\s*\n)[\s\S]*?(?:\n{2,}|\n*$)'
)
_LIST_ITEM = re.compile(
    r'^(( {0,3})(?:[\*\+-]|\d+[.)])(?: *| +[^\n]+)\n+'
    r'(?:\2 +[^\n]+\n+)*)',
    flags=re.M
)
_LIST_BULLET = re.compile(r'^ *(?:[*+-]|\d+[.)]) ?')


class BlockParser(ScannerParser):
    scanner_cls = Matcher

    DEF_LINK = re.compile(
        r'^ *\[([^^\]]+)\]: *'  # [key]:
        r'<?([^\s>]+)>?'  # <link> or link
        r'(?: +["(]([^\n]+)[")])? *\n+'
    )
    DEF_FOOTNOTE = re.compile(
        r'^\[\^([^\]]+)\]: *('
        r'[^\n]*\n+'  # [^key]:
        r'(?: {1,}[^\n]*\n+)*'
        r')'
    )

    AXT_HEADING = re.compile(
        r' {0,3}(#{1,6})(?:\n+|'
        r'\s*(.*?)(?:\n+|\s+?#+\s*\n+))'
    )
    SETEX_HEADING = re.compile(r'([^\n]+)\n *(=|-){2,} *\n+')
    THEMATIC_BREAK = re.compile(
        r' {0,3}((?:- *){3,}|'
        r'(?:_ *){3,}|(?:\* *){3,})\n+'
    )

    INDENT_CODE = re.compile(r'(?: {4}[^\n]+\n*)+')
    FENCED_CODE = re.compile(
        r' {0,3}(`{3,}|~{3,})([^`\n]*)\n'
        r'(?:|([\s\S]*?)\n)'
        r'(?: {0,3}\1[~`]* *\n+|$)'
    )
    BLOCK_QUOTE = re.compile(r'( {0,3}>[^\n]+(\n[^\n]+)*\n*)+')

    BLOCK_HTML = re.compile((
        r' {0,3}(?:'
        r'<(script|pre|style)[\s>][\s\S]*?(?:</\1>[^\n]*\n+|$)|'
        r'<!--(?!-?>)[\s\S]*?-->[^\n]*\n+|'
        r'<\?[\s\S]*?\?>[^\n]*\n+|'
        r'<![A-Z][\s\S]*?>[^\n]*\n+|'
        r'<!\[CDATA\[[\s\S]*?\]\]>[^\n]*\n+'
        r'|' + _BLOCK_HTML_RULE6 + '|' + _BLOCK_HTML_RULE7 + ')'
    ), re.I)

    LIST = re.compile(
        r'(?:( {0,3})\*(?: *| +(?!(?:\* *){2,}\n+)[^\n]+)\n+'
        r'(?:\1 +[^\n]+\n+)*)+|'

        r'(?:( {0,3})\-(?: *| +(?!(?:\- *){2,}\n+)[^\n]+)\n+'
        r'(?:\2 +[^\n]+\n+)*)+|'

        r'(?:( {0,3})\+(?: *| +[^\n]+)\n+'
        r'(?:\3 +[^\n]+\n+)*)+|'

        r'(?:( {0,3})\d{0,9}\.(?: *| +[^\n]+)\n+'
        r'(?:\4 +[^\n]+\n+)*)+|'

        r'(?:( {0,3})\d{0,9}\)(?: *| +[^\n]+)\n+'
        r'(?:\5 +[^\n]+\n+)*)+'
    )

    RULE_NAMES = (
        'indent_code', 'fenced_code',
        'axt_heading', 'setex_heading', 'thematic_break',
        'block_quote', 'block_html', 'list',
        'def_link', 'def_footnote',
    )

    def parse_indent_code(self, m, state):
        # TODO: clean leading spaces
        code = m.group(0)
        return self.tokenize_block_code(code, None, state)

    def parse_fenced_code(self, m, state):
        lang = m.group(2)
        code = m.group(3)
        return self.tokenize_block_code(code, lang, state)

    def tokenize_block_code(self, code, lang, state):
        token = {'type': 'block_code', 'raw': code}
        if lang:
            token['params'] = (lang, )
        return token

    def parse_axt_heading(self, m, state):
        level = len(m.group(1))
        text = m.group(2)
        return self.tokenize_heading(text, level, state)

    def parse_setex_heading(self, m, state):
        level = 1 if m.group(2) == '=' else 2
        text = m.group(1)
        return self.tokenize_heading(text, level, state)

    def tokenize_heading(self, text, level, state):
        return {'type': 'heading', 'text': text, 'params': (level,)}

    def parse_thematic_break(self, m, state):
        return {'type': 'thematic_break', 'blank': True}

    def parse_block_quote(self, m, state):
        depth = state.get('in_block_quote', 0) + 1
        if depth > 5:
            rules = list(self.default_rules)
            rules.remove('block_quote')
        else:
            rules = None

        state['in_block_quote'] = depth
        text = _BLOCK_QUOTE_LEADING.sub('', m.group(0))
        children = self.parse(text, state, rules)
        state['in_block_quote'] = depth - 1
        return {'type': 'block_quote', 'children': children}

    def parse_list(self, m, state):
        text = m.group(0)

        depth = state.get('in_list', 0) + 1
        if depth > 5:
            rules = list(self.default_rules)
            rules.remove('list')
        else:
            rules = None

        state['in_list'] = depth

        children = list(self.parse_list_items(text, state))
        for tok in children:
            if tok['text']:
                text = tok.pop('text')
                tok['children'] = self.parse(text, state, rules)

        state['in_list'] = depth - 1
        token = {'type': 'list', 'children': children}
        state['tight'] = None
        return token

    def parse_list_items(self, text, state):
        items = _LIST_ITEM.findall(text)

        tight = True
        for text, leading in items:
            text_length = len(text)
            text = _LIST_BULLET.sub('', text)
            if tight:
                line_count = text.count('\n\n')
                if line_count > 1:
                    tight = False
                elif line_count == 1 and len(items) > 1:
                    tight = False

            if not text.strip():
                yield {'type': 'list_item', 'text': ''}
                continue

            # outdent
            if '\n ' in text:
                space = text_length - len(text)
                pattern = re.compile(r'^ {1,%d}' % space, flags=re.M)
                text = pattern.sub('', text)

            yield {'type': 'list_item', 'text': text}
        state['tight'] = tight

    def parse_block_html(self, m, state):
        html = m.group(0).rstrip()
        return {'type': 'block_html', 'raw': html}

    def parse_def_link(self, m, state):
        key = m.group(1).lower()
        link = m.group(2)
        title = m.group(3)
        if key not in state['def_links']:
            state['def_links'][key] = (link, title)

    def parse_def_footnotes(self, m, state):
        key = m.group(1).lower()
        if key not in state['def_footnotes']:
            state['def_footnotes'][key] = m.group(2)

    def parse_footnote_item(self, text):
        if '\n' not in text:
            children = [{'type': 'paragraph', 'text': text}]
        else:
            # TODO: parse again
            children = [{'type': 'paragraph', 'text': text}]
        return {'type': 'footnote_item', 'children': children}

    def parse_text(self, text, state):
        if state.get('tight') is True:
            return {'type': 'text', 'text': text.strip()}

        tokens = []
        for p in _LINE_BREAK.split(text):
            p = p.strip()
            if p:
                tokens.append({'type': 'paragraph', 'text': p})
        return tokens

    def parse(self, s, state, rules=None):
        if rules is None:
            rules = self.default_rules

        tokens = []
        for tok in self._scan(s, state, rules):
            if isinstance(tok, dict):
                tokens.append(tok)
            elif tok and isinstance(tok, list):
                tokens.extend(tok)

        return tokens

    def render(self, tokens, inline, state):
        data = self._iter_render(tokens, inline, state)
        if inline.renderer.IS_TREE:
            return list(data)
        return ''.join(data)

    def _iter_render(self, tokens, inline, state):
        for tok in tokens:
            method = inline.renderer._get_method(tok['type'])
            if 'blank' in tok:
                yield method()
                return

            if 'children' in tok:
                children = self.render(tok['children'], inline, state)
            elif 'raw' in tok:
                children = tok['raw']
            else:
                children = inline(tok['text'], state)
            params = tok.get('params')
            if params:
                yield method(children, *params)
            else:
                yield method(children)
