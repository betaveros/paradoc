from paradoc.objects import Environment

name_template = """{{#chars}}{{#sp}}<code>{{/sp}}{{text}}{{#sp}}</code>{{/sp}}{{/chars}}"""

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
h2 { font-family: monospace; }
h2 code { font-size: 75%; border: 1px dotted black; background: #ccc; }
pre.ex, pre.exs { border: 1px solid #ac9; background-color: #eeffcc; padding: 0.2em; }
pre.ex::before  { content: "Example: ";  font-size: 75%; font-family: sans-serif; }
pre.exs::before { content: "Examples: "; font-size: 75%; font-family: sans-serif; display: block; }
</style>
</head>
<body>
<div class="wrap">
<h1>Paradoc Built-Ins</h1>
{{#vars}}
<h2>{{{escaped_name}}}</h2>
<em>Stability: {{stability}}</em>
{{{docs}}}
{{/vars}}
</div>
</body>
</html>
"""

def document(env: Environment) -> None:
    import pystache

    def escape_name(name: str) -> str:
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
        return pystache.render(name_template, {'chars': chars})

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

    data = []
    for name, obj in sorted(env.vars.items()):
        data.append({
            'escaped_name': escape_name(name),
            'stability': getattr(obj, 'stability', 'unknown'),
            'docs': render_docs(str(getattr(obj, 'docs', ''))),
        })
    print(pystache.render(template, {'vars': data}))
