from typing import *
from paradoc.objects import Environment
from paradoc.trailer import Trailer
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
<title>Paradoc Trailers and Built-Ins</title>
<style>
body { font-family: sans-serif; margin: 0; background-color: #eee; }
.wrap { background-color: #fff; margin-left: auto; margin-right: auto; padding: 1em; max-width: 48em; }
h2 { padding-top: 0.5em; border-top: 3px double black; }
h3 { font-family: monospace; border-top: 1px dashed black; padding-top: 0.5em; }
h3 a { text-decoration: none; }
h3 code.char { font-size: 75%; border: 1px dotted black; background: #ccc; }
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
<h1>Paradoc Trailers and Built-Ins</h1>
<p>Crude definitions on stability: Stable means you can almost certainly expect
this feature to be in Paradoc pretty much as-is, but we reserve the possibility
of adding/changing behavior in cases it previously did not cover, in ways that
might technically not be backwards-compatible.</p>
<p>Beta means you can probably expect this to be in Paradoc as-is, but should
also be prepared for it to be renamed or have its behavior changed. Or, there
may be known bugs/design issues/TODOs in its implementation, or it may not have
been tested as thoroughly as a stable feature.</p>
<p>Alpha means this is likely to be in Paradoc, but its name or some aspects of
its behavior are decidedly not final. It may be replaced with something only
spiritually similar.</p>
<p>For unstable features, all bets are off...</p>
<p>Of course, until we hit version 1.0 (hahahaha), nothing should be considered
absolutely fixed.</p>
</p>
<p><strong>NOTE: The ids of elements on this page should be considered
unstable.</strong></p>
<h2>Table of Contents</h2>
<ul>
{{#trailer_families}}
<li><a href="#{{id}}">{{name}} Trailers</a></li>
{{/trailer_families}}
<li><a href="#GV">Built-Ins</a></li>
</ul>

{{#trailer_families}}
<h2 id="{{id}}">{{name}} Trailers</h2>
{{#family}}
<h3 id="{{id}}">{{{formatted_name}}}</h3>
<p class="stability {{stability}}">Stability: {{stability}}</p>
{{{alias_note}}}
{{{docs}}}
{{/family}}
{{/trailer_families}}

<h2 id="GV">Built-Ins</h2>
{{#vars}}
<h3 id="{{id}}">{{{formatted_name}}}</h3>
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
def mangle_to_id(id_prefix: str, name: str) -> str:
    acc = [id_prefix, '_'] # type: List[str]
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

def document(env: Environment,
        trailer_families: List[Tuple[str, Dict[str, Trailer]]]) -> None:
    import pystache

    def format_name(id_prefix: str, name: str) -> str:
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
                {'id': mangle_to_id(id_prefix, name), 'chars': chars})

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

    def render_alias_note(id_prefix: str, aliases: List[str]) -> str:
        if aliases:
            return ('<p class="aliases">Aliases: ' +
                    ", ".join(format_name(id_prefix, alias) for alias in aliases) +
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

        stability_index = ['unstable', 'alpha', 'beta', 'stable'].index(stability)
        data.append({
            'id': mangle_to_id('V', name),
            'formatted_name': format_name('V', name),
            'stability': stability,
            'stability_index': stability_index,
            'docs': render_docs(docs),
            'value_data': value_data,
            'alias_note': render_alias_note('V', aliases)
        })

    trailer_data = []
    for family_name, trailer_list in trailer_families:
        family_data = []
        fc = family_name[0]
        for name0, trailer in sorted(trailer_list.items()):
            aliases = ['_' + alias for alias in trailer.aliases if alias != name0]
            name = '_' + name0
            family_data.append({
                'id': mangle_to_id(fc, name),
                'formatted_name': format_name(fc, name),
                'stability': trailer.stability,
                'docs': render_docs(trailer.docs or ''),
                'alias_note': render_alias_note(fc, aliases),
            })
        trailer_data.append({
            'name': family_name,
            'id': 'G' + fc,
            'family': family_data,
        })

    print(pystache.render(template, {
        'vars': data,
        'trailer_families': trailer_data
    }))
    # print(pystache.render(template, {'vars': sorted(data, key=lambda d: -d['stability_index'])}))
