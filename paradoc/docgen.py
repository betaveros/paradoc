from typing import List
from paradoc.objects import Environment
import string

name_template = """<a href="#{{id}}"><code>{{#chars}}{{#sp}}<code class="char">{{/sp}}{{text}}{{#sp}}</code>{{/sp}}{{/chars}}</code></a>"""

docs_template = """
{{#pars}}
<{{tag}} class="{{cls}}">{{text}}</{{tag}}>
{{/pars}}
"""

template = """
<html lang="en">
<head>
<meta charset="utf-8">
<title>Paradoc Built-Ins</title>
<style>
body { font-family: sans-serif; margin: 0; background-color: #eee; }
.wrap { background-color: #fff; margin-left: auto; margin-right: auto; padding: 1em; max-width: 48em; }
h2 { font-family: monospace; border-top: 1px dashed black; padding-top: 0.5em; }
h2 a { text-decoration: none; }
h2 code.char { font-size: 75%; border: 1px dotted black; background: #ccc; }
pre.ex, pre.exs { border: 1px solid #ac9; background-color: #eeffcc; padding: 0.2em; }
pre.ex::before, pre.exs::before { font-size: 75%; font-family: sans-serif; }
pre.ex::before { content: "Example: "; }
pre.exs::before { content: "Examples: "; display: block; }
p.const { border: 1px solid #ccc; background-color: #eee; padding: 0.2em; }

p.aliases, p.stability { font-style: italic; margin-left: 2.5em; }
p.aliases a { text-decoration: none; }
p.aliases code.char { font-size: 75%; border: 1px dotted black; background: #ccc; }
p.unstable { color: #c00; }
p.alpha { color: #c60; }
p.beta { color: #088; }
p.stable { color: #0a0; }
</style>
</head>
<body>
<div class="wrap">
<h1>Paradoc Built-Ins</h1>
{{#vars}}
<h2 id="{{id}}">{{{formatted_name}}}</h2>
<p class="stability {{stability}}">Stability: {{stability}}</p>
{{{alias_note}}}
{{{docs}}}
{{#value_data}}
<p class="const">{{type}} constant with value <code>{{value}}</code></p>
{{/value_data}}
{{/vars}}
</div>
</body>
</html>
"""


safe_id_chars = string.ascii_letters + string.digits
def mangle_to_id(name: str) -> str:
    acc = [] # type: List[str]
    for c in name:
        if c in safe_id_chars:
            acc.append(c)
        elif c == '_':
            acc.append('__')
        else:
            acc.append('_' + hex(ord(c))[2:] + '_')
    ret = ''.join(acc)
    if ret.endswith('_'): ret = ret[:-1]
    return ret

def document(env: Environment) -> None:
    import pystache

    def format_name(name: str) -> str:
        chars = []
        for c in name:
            if c == "\r":
                chars.append({'sp': True, 'text': 'RETURN'})
            if c == "\n":
                chars.append({'sp': True, 'text': 'NEWLINE'})
            elif c == " ":
                chars.append({'sp': True, 'text': 'SPACE'})
            elif c == "\t":
                chars.append({'sp': True, 'text': 'TAB'})
            else:
                chars.append({'text': c})
        return pystache.render(name_template,
                {'id': mangle_to_id(name), 'chars': chars})

    def render_docs(docs: str) -> str:
        docpars = docs.split('\n\n')
        render_pars = []
        for par0 in docpars:
            text = par0.strip()
            tag = "p"
            cls = ""
            if text.startswith('ex:'):
                tag = "pre"
                lines = text[3:].splitlines()
                cls = 'exs' if len(lines) > 1 else 'ex'
                text = '\n'.join(s.strip() for s in lines)
            render_pars.append({'tag': tag, 'cls': cls, 'text': text})
        return pystache.render(docs_template, {'pars': render_pars})

    def render_alias_note(aliases: List[str]) -> str:
        if aliases:
            return ('<p class="aliases">Aliases: ' +
                    ", ".join(format_name(alias) for alias in aliases) +
                    '</p>')
        else:
            return ''

    data = []
    for name, obj in sorted(env.vars.items()):
        aliases = [alias for alias in getattr(obj, 'aliases', []) if alias != name]
        docs = getattr(obj, 'docs', None) or env.var_docs.get(name) or ''
        stability = getattr(obj, 'stability', None) or env.var_stability.get(name) or 'unknown'

        if isinstance(obj, int):
            value_data = { 'type': 'Integer', 'value': obj }
        elif isinstance(obj, float):
            value_data = { 'type': 'Float', 'value': obj }
        elif isinstance(obj, str):
            value_data = { 'type': 'String', 'value': repr(obj) }
        else:
            value_data = {}

        data.append({
            'id': mangle_to_id(name),
            'formatted_name': format_name(name),
            'stability': stability,
            'docs': render_docs(docs),
            'value_data': value_data,
            'alias_note': render_alias_note(aliases)
        })
    print(pystache.render(template, {'vars': data}))
