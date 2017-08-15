from typing import *
from paradoc.objects import Environment
from paradoc.trailer import Trailer
import string

name_template = """<a href="#{{id}}"><code>
{%- for char in chars -%}
    {%- if char.sp -%}
        <code class="char">{{ char.text }}</code>
    {%- else -%}
        {{ char.text }}
    {%- endif -%}
{%- endfor -%}
</code></a>"""

docs_template = """
{% for par in pars %}
<{{ par.tag }} class="{{ par.cls }}">{{ par.text }}</{{ par.tag }}>
{% endfor %}
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
{% for family in trailer_families %}
<li><a href="#{{ family.id }}">{{ family.name }} Trailers</a></li>
{% endfor %}
<li><a href="#GV">Built-Ins</a></li>
</ul>

{% for family in trailer_families %}
<h2 id="{{ family.id }}">{{ family.name }} Trailers</h2>
{% for trailer in family.trailers %}
<h3 id="{{ trailer.name|tid(family.name) }}">{{ trailer.name|t(family.name) }}</h3>
<p class="stability {{ trailer.stability }}">Stability: {{ trailer.stability }}</p>
{% if trailer.aliases %}
<p class="aliases">Aliases:
{% for alias in trailer.aliases -%}
{{ alias|t(family.name) }}{%- if not loop.last -%}, {% endif -%}
{%- endfor %}
</p>
{% endif %}
{{ trailer.docs }}
{% endfor %}
{% endfor %}

<h2 id="GV">Built-Ins</h2>
{% for var in vars %}
<h3 id="{{ var.name|bid }}">{{ var.name|b }}</h3>
<p class="stability {{ var.stability }}">Stability: {{ var.stability }}</p>
{% if var.aliases %}
<p class="aliases">Aliases:
{% for alias in var.aliases -%}
{{ alias|b }}{%- if not loop.last -%}, {% endif -%}
{%- endfor %}
</p>
{% endif %}
{{ var.docs }}
{% if var.value %}
<p class="const">{{ var.type }} constant with value <code>{{ var.value }}</code></p>
{% endif %}
{% endfor %}
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
    import jinja2
    from jinja2 import Markup

    jenv = jinja2.Environment(autoescape=True)

    name_jt = jenv.from_string(name_template)

    def link_name(id_prefix: str, name: str, is_trailer: bool) -> Markup:
        chars = [] # type: List[dict]
        if is_trailer: chars.append({'text': '_'})
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

        return Markup(name_jt.render({
            'id': mangle_to_id(id_prefix, name), 'chars': chars
        }))

    def link_builtin(name: str) -> Markup:
        return link_name('V', name, False)
    def link_trailer(name: str, family: str) -> Markup:
        return link_name(family[0], name, True)

    def mangle_builtin_id(name: str) -> str:
        return mangle_to_id('V', name)
    def mangle_trailer_id(name: str, family: str) -> str:
        return mangle_to_id(family[0], name)

    jenv.filters['b'] = link_builtin
    jenv.filters['t'] = link_trailer
    jenv.filters['bt'] = lambda name: link_trailer(name, 'Block')
    jenv.filters['st'] = lambda name: link_trailer(name, 'String')
    jenv.filters['it'] = lambda name: link_trailer(name, 'Int')
    jenv.filters['ft'] = lambda name: link_trailer(name, 'Float')
    jenv.filters['bid'] = mangle_builtin_id
    jenv.filters['tid'] = mangle_trailer_id

    docs_jt = jenv.from_string(docs_template)
    main_jt = jenv.from_string(template)

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
            else:
                text = Markup(jenv.from_string(text).render())
            render_pars.append({'tag': tag, 'cls': cls, 'text': text})
        return Markup(docs_jt.render({
            'pars': render_pars
        }))

    data = []
    for name, obj in sorted(env.vars.items()):
        aliases = [alias for alias in getattr(obj, 'aliases', []) if alias != name]
        docs = getattr(obj, 'docs', None) or env.var_docs.get(name) or ''
        stability = getattr(obj, 'stability', None) or env.var_stability.get(name) or 'unknown'

        stability_index = ['unstable', 'alpha', 'beta', 'stable'].index(stability)
        datum = {
            'name': name,
            'stability': stability,
            'stability_index': stability_index,
            'docs': render_docs(docs),
            'aliases': aliases,
        }

        if isinstance(obj, int):
            datum['type'] = 'Integer'; datum['value'] = obj
        elif isinstance(obj, float):
            datum['type'] = 'Float'; datum['value'] = obj
        elif isinstance(obj, str):
            datum['type'] = 'String'; datum['value'] = repr(obj)

        data.append(datum)

    trailer_data = []
    for family_name, trailer_list in trailer_families:
        family_data = []
        for name, trailer in sorted(trailer_list.items()):
            aliases = [alias for alias in trailer.aliases if alias != name]
            family_data.append({
                'name': name,
                'stability': trailer.stability,
                'docs': render_docs(trailer.docs or ''),
                'aliases': aliases,
            })
        trailer_data.append({
            'name': family_name,
            'id': 'G' + family_name,
            'trailers': family_data,
        })

    print(main_jt.render({
        'vars': data,
        'trailer_families': trailer_data
    }))
    # print(pystache.render(template, {'vars': sorted(data, key=lambda d: -d['stability_index'])}))
