from typing import List, Tuple, Dict
from paradoc.objects import Environment
from paradoc.trailer import Trailer
import string, sys

introduction = """
*Because there aren't enough golfing languages already™*

Paradoc is a golfing language in the stack-based lineage of GolfScript, heavily
inspired by it and CJam. Other inspirations include 05AB1E, Jelly, Pyth, and
rhoScript.

Like many of these other things, Paradoc is a work in progress. Still, I like
to think we have some pretty reasonable documentation.

Some example programs:

Hello, world! (unterminated strings are on the TODO list)

    "Hello, world!"

Print squares from 0 to 100, separated by spaces

    sE²m                 .. 4 bytes (if encoded as CP1252)
    sE2pm                .. 5 ASCII characters
    _space 11 Square_map .. Expanded version

Print Fibonacci numbers from 0 to 89, separated by spaces:

    s0 1T+kx .. 8 bytes / ASCII characters
    s•1T+kx  .. 7 bytes in CP1252
    _space 0 1 10 +_keep_xloop .. Expanded version

### Usage

Paradoc is written in Python 3 (and uses [mypy (optional static typing)
annotations](http://mypy-lang.org/) extensively). REPL:

    python3 -m paradoc

Run a file:

    python3 -m paradoc source_file.prdc

Evaluate a command:

    python3 -m paradoc -e "sE2pm"

### Design Philosophy

In decreasing order of importance:

-   The most important design goal for Paradoc is that **programs should be
    writable in a natural literate style** without much effort, even for
    complicated problems, although the naturally resulting programs may not
    lend themselves to immediate golfing. This includes both naming,
    formatting, and structure of logic.

    Of course, with its unusual order of operations, stack-based language can
    only be so natural to write in. The biggest non-negotiable concrete
    consequence, though, is that Paradoc **must have support for long
    alphabetic identifiers**. This is something GolfScript did that, based on
    what I've seen, most of its descendants and more recent golfing languages
    have abandoned in favor of optimizing for brevity. While the reduction in
    short identifier namespace/usability certainly puts Paradoc at a
    disadvantage for achieving that low golf score, I am OK with that tradeoff
    in order to make coding directly in Paradoc easier. Even then, I don't
    think Paradoc has sacrificed very much golfability in its design.

    Specifically, Paradoc supports (admittedly somewhat bizarre)
    `Capitalized_snake_case` identifiers of arbitrary length. It treats the
    underscore as a lowercase letter and parses identifiers as one capital
    letter followed by zero or more lowercase letters. Happily, this frees up
    the lowercase letter to perform a host of other useful effects on other
    things.

    Another corollary is that Paradoc **must have support for legible
    comments**: towards that end, you can start a simple end-of-line comment
    with `..`, which is pretty visually clean as end-of-line comment markers
    go, in my opinion.

-   The definitions, names, and behavior of built-ins and variables should be
    **simple, predictable, and consistent**. When the most obvious mnemonic
    names are not possible, they should at least be consistent; for example,
    `x` and `*` perform similar operations because they look similar, the
    letter D ("downward") consistently reverses lists, and variants of `A` and
    `O` refer to maximum and minimum respectively.

    A more specific rule is that **everything must have a mnemonic**. Paradoc
    will not, for example, use ¾ to do something unrelated to 3, 4, or
    fractions. Fortunately, mnemonics are not *that* hard to make.

    Another specific concrete consequence: Built-ins should never read an
    integer constant from the stack in order to select one of several
    completely dissimilar operations. Compared to the other golfing languages,
    this is pretty much not an issue at all, since we allow alphabetic
    identifiers of arbitrary length and are thus in no danger of running out of
    identifiers.

    Consistency internal to Paradoc is slightly more important than
    simplicity/predictability from an external viewpoint. For example, if there
    are two namespaces in which we want to define a similar operation, and
    there's a name with an easy mnemonic available in only one namespace and a
    name with an awkward mnemonic available in both namespaces, we will prefer
    to use the awkward name in both namespaces.

-   When none of the above concerns apply, Paradoc should be similar to
    pre-existing languages, mostly GolfScript/CJam but also Python (so
    Ruby/Java-isms may need to be replaced with their Python counterparts). A
    notable example is that `*` no longer folds/joins; instead we have `R` (for
    "reduce", which is what the corresponding function in Python is called),
    and allows `*` on a block and an integer `n` to behave consistently with
    `*` on a block and the half-open range `[0..n)`, a coercion made by many
    built-ins.

-   Literate programs should not be totally different modes of the
    parser/interpreter (contrast rhoScript or "big Pyth"). Literate Paradoc and
    golfed Paradoc should just be styles of programming used by the programmer
    that can coexist in one program, and it should be possible to manually
    translate between them.

-   Debugging, at least printf-style debugging if not more, should be natural
    and easy.

-   Paradoc should be golfable. Obviously this is important (and is the reason
    for the choice of identifiers), but it should not override the above
    concerns.

-   Although Paradoc uses characters from the common Windows-1252 encoding, its
    golfability (in terms of number of bytes) should degrade gracefully when
    restricted to being written in UTF-8 or even ASCII.

    There also exist a few control codes that we have been replaced with custom
    characters, although this is still quite unstable.

### Differences from GolfScript/CJam

-   Paradoc parses tokens differently; **identifiers** begin with either a
    symbol (excluding the underscore and various other characters taken in the
    syntax) or an uppercase letter, and are followed by zero or more lowercase
    letters or underscores.

-   Like CJam, Paradoc uses single quotes to escape and push the following
    character, no matter what it is.

-   Paradoc swaps `.` and `:` from GolfScript/CJam, using `.` for assignment
    and `:` for duplicating top of stack. Rationale: I think `:` is more
    mnemonic for "duplicate" since there are two dots (Befunge also uses it),
    and it feels more like an inverse to `;`. At the same time, this clears up
    some corners of the syntax more elegantly. First, it allows us to parse
    numbers starting with a decimal point like `.618`, and it allows us to
    begin end-of-line comments with `..`, which are a high priority for
    Paradoc, easy to type, and not visually noisy.

-   In Paradoc, `+` on a list and block filters the list by the block, instead
    of `,`. This is to allow symmetry with `-`, which filters *out* elements
    from the list that satisfy the block. `,` instead filters the lists and
    returns the *indexes* of elements that satisfy the block. Further, `,` on a
    list zips it with its indices; instead, `L` computes the length of a list.

-   In Paradoc, `R` joins sequences with other sequences and reduces/folds
    lists by a block, instead of `*`, which instead repeats a block over a list
    or the half-open range `[0..n)`, without pushing anything onto the stack,
    but instead putting each element into the special variable `X`. This allows
    `*` to behave consistently on integers `n` and half-open ranges `[0..n)`,
    and for it to perform the more intuitive Cartesian products on sequences.

-   In Paradoc, `@` and `#` are changed to what I consider more mnemonic
    operations. `@` finds the index of an element or substring in a sequence
    (so it figures out where the element is **at**) and `#` counts the
    **number** of occurrences of that element of substring. Exponentiation is
    relegated to the (non-ASCII character) `ˆ` or `*p`, which seems a more
    reasonable mnemonic anyway (although I thought the audial mnemonic of
    **Pound** for `#` and **Power** was pretty reasonable) and allows it to
    also perform list exponentiation in the sense of Cartesian products. There
    is currently no one-character built-in for the stack-manipulation analogue
    of `@` in GolfScript/CJam.

-   Most of the alphabetic built-ins are different, of course.

"""

syntax = """
-   **End-of-line comments** start with two periods `..` or two em dashes `——`.

    A shebang line at the start of a file is also considered an end-of-line
    comment.

-   **Strings** are delimited by double quotes. Inside a string literal, the only
    special characters are double quotes and backslashes, the latter of which
    escape double quotes and themselves, and nothing else. (So multiline string
    literals are totally fine.) Normally, they simply push themselves onto the
    stack.

-   **Characters** consist of a single quote followed by a single character. No
    characters are special.

-   **Numbers** consist mostly of ASCII digits. There can be a decimal point, and
    it can start the numeric literal, but if there is one, there must be at least
    one digit after it. Scientific notation is supported.

    Numeric literals can be preceded by an **em dash** (`—`, U+2014) to make them
    negative. (Alternatively, you can also append an `m`; more on that later.)

-   **Curly braces** delimit code blocks. Code is parsed inside of them, and they
    nest.

-   Assignment is performed with the period `.` or the em dash `—`, and assigns
    the value on top of the stack to the following identifier.

-   Identifiers consist of an "uppercase letter" followed by zero or more
    "lowercase letters" or underscores.

    Paradoc considers most symbols to be uppercase letters, including whitespace.
    Lowercase letters include the typical ASCII lowercase letters and other
    lowercase letters in CP1252. Digits and underscores are neither.

-   A very important syntactic concept is a **trailer**, which basically refers
    to sequences of lowercase letters directly following some other token.
    Trailers modify the behavior of the token they follow. A trailer consists of
    either a single lowercase letter or an underscore followed by zero or more
    lowercase letters.

    For example, there is a block trailer called `_bind` or `b`. You can modify
    the built-in block `+` by appending it, to get `+b` or `+_bind`, which does
    something related to `+`. Trailers can be chained; `+bm` is `+` with the
    trailers `b` and `m`.

    Note that this means identifiers are actually ambiguous. If you write
    `Dup`, how does Paradoc if you mean the identifier `Dup`, or a built-in
    called `Du` with a trailer `p`, or a built-in called `D` with two trailers,
    `u` and `p`? The answer is that Paradoc doesn't know this, and simply tries
    each of these possibilities in turn until it finds an identifier that it
    has something associated with. Then it applies (or tries to apply) all of
    the trailers following it.

    More precisely, when Paradoc encounters an identifier, it first tries to
    look up the entire identifier. While this fails, if the identifier has an
    underscore, it cuts off the part including and after the last underscore,
    and if not it cuts off the last (lowercase) letter. It treats the part it
    cut off as a trailer. It repeats this process, cutting off trailers, until
    it finds an identifier that it can look up. Then it applies all the
    trailers it cut off in the order they appear in the source (the reverse of
    the order in which they were cut off).

    Not all trailers for all letters exist for all types. If Paradoc finds an
    identifier but fails to apply the trailers following it, it does not keep
    examining shorter identifiers.

There are also global trailers, which come right at the start of the program.
These haven't been documented yet, sorry."""

semantics = """
Paradoc is stack-based. It starts with an empty stack and just runs each thing
in the code in sequence. Things run on the stack.

The data types are ints, floats, Chars, strings, (heterogeneous) lists, and
blocks (executable things). When Paradoc sees an identifier, it modifies it
with trailers, if any, and then executes it if it's a block and the final
trailer is not **reluctant**.

### Marks

Paradoc keeps track of **marks** in the stack, which you can create with `[`.
These are usually placed for `]` to be called later and collect elements above
the last mark into a list. If a mark is at the top of the stack and an element
is popped, it moves down; if elements are pushed after it, it stays below them.

Note that many higher-order functions and the like will execute a block in a
protected *"shadow" stack* that start with a mark in it. Although the shadow
stack "bottoms out" into the underlying stack, so trying to pop from the shadow
stack when it's empty will pop from the underlying stack instead, the mark will
not leave the shadow stack, and its presence or absence won't affect the
underlying stack when it's destroyed. This way, something like `]z` does the
right thing.

There are a few variations of shadow stacks, but these are kind of
implementation details.

### The X-Stack

A handful of identifiers are specially aliased to the X-stack, a place where
the current element/index being operated on is pushed in most loops.

Usually, an element and an index are pushed together, the element on top. As
you'd expect, elements higher on the stack are easier to access. `X` is the top
element, `Y` is the second-to-top (so usually the index), `Z` is the third;
these names are pretty stable. The following elements currently go `Xx`, `Xy`, `Xz`, `Yx`, `Yy`, `Yz`, etc, but they should be considered unstable.

See `*` for examples.

### Input

Note that there's no implicit input; however, global trailers can configure an
**input trigger**, the result of which is that when you try to pop from an
empty stack, Paradoc will read input and offer it to you as the result of the
pop. (Note that you will pop things in the order they're read, which is the opposite
order of how lists are usually ordered on the stack!)

You can also explicitly read input with `V`.
"""

mnemonics = """
-   Mostly we pretend Python lists are called **Arrays** and use the letter A.
-   **D** is for Down, which is all sorts of Reversing.
-   **A** is for **max** and **O** is for **min**. You can think l**A**rge and
    sm**O**l.
-   **R** is for **Reduce**, which covers the higher-order function called
    reduce or fold as well as joining strings/lists together with something in
    between.
-   **S** sometimes refers to **substrings** and **slicing**.
-   As in Lisp, many built-ins use the last letter **p** for **predicate**, as
    in a test for some quality that returns true or false, generally
    represented by 1 and 0, respectively.
"""

stability_text = """
As noted, Paradoc is a work in progress, so although there is autogenerated
documentation here for all the built-ins, they are all subject to change. Some
of then are more likely to change than others, though, so each one is labeled
with a stability. Here are my crude definitions of the stabilities:

-   Stable means you can almost certainly expect this feature to be in Paradoc
    pretty much as-is, but we reserve the possibility of adding/changing behavior
    in cases it previously did not cover, in ways that might technically not be
    backwards-compatible, or of changing the long expository identifier alias.

-   Beta means you can probably expect this to be in Paradoc as-is, but should
    also be prepared for it to be renamed or have its behavior changed. Or, there
    may be known bugs/design issues/TODOs in its implementation, or it may not
    have been tested as thoroughly as a stable feature.

-   Alpha means this is likely to be in Paradoc, but its name or some aspects of
    its behavior are decidedly not final. It may be replaced with something only
    spiritually similar.

-   For unstable features, all bets are off...

-   Of course, until we hit version 1.0, nothing should be considered
    absolutely fixed; if I have a good reason I will still change stable
    built-ins.

The ids of elements on this page should be considered unstable, so permalinks
to this page should be considered unstable as well.
"""

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
h3 { border-top: 1px dashed black; padding-top: 0.5em; }
h3.name { font-family: monospace; }
h3 a { text-decoration: none; }
h3 code.char { font-size: 75%; border: 1px dotted black; background: #ccc; }
pre { border: 1px solid #ac9; background-color: #eeffcc; padding: 0.2em; }
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
<h1>Paradoc Documentation and Built-Ins</h1>
<strong>Version {{ version }}</strong>
<h2>Table of Contents</h2>
<ul>
<li><a href="#GIntroduction">Introduction</a></li>
<li><a href="#GSyntax">Syntax</a></li>
<li><a href="#GSemantics">Semantics</a></li>
<li><a href="#GMnemonics">Mnemonics</a></li>
<li><a href="#GStability">Stability</a></li>
{% for family in trailer_families %}
<li><a href="#{{ family.id }}">{{ family.name }} Trailers</a></li>
{% endfor %}
<li><a href="#GV">Built-Ins</a></li>
</ul>

<h2 id="GIntroduction">Introduction</h2>
{{ introduction }}
<h2 id="GSyntax">Syntax</h2>
{{ syntax }}
<h2 id="GSemantics">Semantics</h2>
{{ semantics }}
<h2 id="GMnemonics">Mnemonics</h2>
{{ mnemonics }}
<h2 id="GStability">Stability</h2>
{{ stability }}

{% for family in trailer_families %}
<h2 id="{{ family.id }}">{{ family.name }} Trailers</h2>
{% for trailer in family.trailers %}
<h3 id="{{ trailer.name|tid(family.name) }}" class="name">{{ trailer.name|t(family.name) }}</h3>
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
<h3 id="{{ var.name|bid }}" class="name">{{ var.name|b }}</h3>
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
    from markdown import markdown
    from paradoc.__version__ import version

    jenv = jinja2.Environment(autoescape=True)

    name_jt = jenv.from_string(name_template)

    linked_names = set()
    id_referenced_names = set()

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
            elif c == "\xa0":
                chars.append({'sp': True, 'text': 'NBSP'})
            elif '\x00' <= c <= '\x1f' :
                chars.append({'sp': True, 'text': '^' + chr(ord(c) + 64)})
            else:
                chars.append({'text': c})

        linked_names.add((id_prefix, name))
        return Markup(name_jt.render({
            'id': mangle_to_id(id_prefix, name), 'chars': chars
        }))

    def link_builtin(name: str) -> Markup:
        return link_name('V', name, False)
    def link_trailer(name: str, family: str) -> Markup:
        return link_name(family[0], name, True)

    def mangle_builtin_id(name: str) -> str:
        id_referenced_names.add(('V', name))
        return mangle_to_id('V', name)
    def mangle_trailer_id(name: str, family: str) -> str:
        id_referenced_names.add((family[0], name))
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
        'version': version,
        'introduction': Markup(markdown(introduction)),
        'syntax': Markup(markdown(syntax)),
        'semantics': Markup(markdown(semantics)),
        'mnemonics': Markup(markdown(mnemonics)),
        'stability': Markup(markdown(stability_text)),
        'vars': data,
        'trailer_families': trailer_data
    }))

    undefined_names = linked_names - id_referenced_names
    if undefined_names:
        print('WARNING!!! Undefined names', undefined_names, file=sys.stderr)
    # print(pystache.render(template, {'vars': sorted(data, key=lambda d: -d['stability_index'])}))

# vim:set tabstop=4 shiftwidth=4 expandtab fdm=marker:
