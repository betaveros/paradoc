Paradoc
=======

*Because there aren't enough golfing languages already™*

Paradoc is a golfing language in the stack-based lineage of GolfScript, heavily inspired by it and CJam. Other inspirations include 05AB1E, Jelly, Pyth, and rhoScript.

Like many of these other things, Paradoc is a work in progress. There will be documentation later :) In the meantime, here are some short snippets:

Hello, world! (unterminated strings are on the TODO list)

    "Hello, world!"

Print squares from 0 to 100, separated by spaces

    sE²m                 .. 4 bytes (if encoded as CP1252)
    sE2pm                .. 5 ASCII characters
    _space 11 Square_map .. Expanded version

Print Fibonacci numbers from 0 to 89, separated by spaces (there will definitely be a 2-byte way to push the initial 0 and 1, but I haven't locked it down yet):

    s0 1T+kx .. 8 bytes / ASCII characters

    _space 0 1 10 +_keep_xloop .. Expanded version

Usage
=====

Paradoc is written in Python 3 (and uses [mypy (optional static typing) annotations](http://mypy-lang.org/) extensively). REPL:

    python3 -m paradoc

Run a file:

    python3 -m paradoc source_file.prdc

Evaluate a command:

    python3 -m paradoc -e "sE2pm"

Design Philosophy
=================

In decreasing order of importance:

- The most important design goal for Paradoc is that **programs should be writable in a natural literate style** without much effort, even for complicated problems, although the naturally resulting programs may not lend themselves to immediate golfing. This includes both naming, formatting, and structure of logic.

  Of course, with its unusual order of operations, stack-based language can only be so natural to write in. The biggest non-negotiable concrete consequence, though, is that Paradoc **must have support for long alphabetic identifiers**. This is something GolfScript did that, based on what I've seen, most of its descendants and more recent golfing languages have abandoned in favor of optimizing for brevity. While the reduction in short identifier namespace/usability certainly puts Paradoc at a disadvantage for achieving that low golf score, I am OK with that tradeoff in order to make coding directly in Paradoc easier. Even then, I don't think Paradoc has sacrificed very much golfability in its design.

  Specifically, Paradoc supports (admittedly somewhat bizarre) `Capitalized_snake_case` identifiers of arbitrary length. It treats the underscore as a lowercase letter and parses identifiers as one capital letter followed by zero or more lowercase letters. Happily, this frees up the lowercase letter to perform a host of other useful effects on other things.

  Another corollary is that Paradoc **must have support for legible comments**: towards that end, you can start a simple end-of-line comment with `..`, which is pretty visually clean as end-of-line comment markers go, in my opinion.
- The definitions, names, and behavior of built-ins and variables should be **simple, predictable, and consistent**. When the most obvious mnemonic names are not possible, they should at least be consistent; for example, `x` and `*` perform similar operations because they look similar, the letter D ("downward") consistently reverses lists, and variants of `A` and `O` refer to maximum and minimum respectively.

  A more specific rule is that **everything must have a mnemonic**. Paradoc will not, for example, use ¾ to do something unrelated to 3, 4, or fractions. Fortunately, mnemonics are not *that* hard to make.

  Another specific concrete consequence: Built-ins should never read an integer constant from the stack in order to select one of several completely dissimilar operations. Compared to the other golfing languages, this is pretty much not an issue at all, since we allow alphabetic identifiers of arbitrary length and are thus in no danger of running out of identifiers.

  Consistency internal to Paradoc is slightly more important than simplicity/predictability from an external viewpoint. For example, if there are two namespaces in which we want to define a similar operation, and there's a name with an easy mnemonic available in only one namespace and a name with an awkward mnemonic available in both namespaces, we will prefer to use the awkward name in both namespaces.

- When none of the above concerns apply, Paradoc should be similar to pre-existing languages, mostly GolfScript/CJam but also Python (so Ruby/Java-isms may need to be replaced with their Python counterparts). A notable example is that `*` no longer folds/joins; instead we have `R` (for "reduce", which is what the corresponding function in Python is called), and allows `*` on a block and an integer `n` to behave consistently with `*` on a block and the half-open range `[0..n)`, a coercion made by many built-ins.
- Literate programs should not be totally different modes of the parser/interpreter (contrast rhoScript or "big Pyth"). Literate Paradoc and golfed Paradoc should just be styles of programming used by the programmer that can coexist in one program, and it should be possible to manually translate between them.
- Debugging, at least printf-style debugging if not more, should be natural and easy.
- Paradoc should be golfable. Obviously this is important (and is the reason for the choice of identifiers), but it should not override the above concerns.
- Although Paradoc uses characters from the common Windows-1252 encoding, its golfability (in terms of number of bytes) should degrade gracefully when restricted to being written in UTF-8 or even ASCII.

  In the future, we may emulate Jelly and fill up the control codes in the Windows-1252 code page with custom characters, but we haven't expanded to that point yet.

Differences from GolfScript/CJam
================================

- Paradoc parses tokens differently; **identifiers** begin with either a symbol (excluding the underscore) or an uppercase letter, and are followed by zero or more lowercase letters.
- Like CJam, Paradoc uses single quotes to escape and push the following character, no matter what it is.
- Paradoc swaps `.` and `:` from GolfScript/CJam, using `.` for assignment and `:` for duplicating top of stack. Rationale: I think `:` is more mnemonic for "duplicate" since there are two dots (Befunge also uses it), and it feels more like an inverse to `;`. At the same time, this clears up some corners of the syntax more elegantly. First, it allows us to parse numbers starting with a decimal point like `.618`, and it allows us to begin end-of-line comments with `..`, which are a high priority for Paradoc, easy to type, and not visually noisy.
- In Paradoc, `+` on a list and block filters the list by the block, instead of `,`. This is to allow symmetry with `-`, which filters *out* elements from the list that satisfy the block. `,` instead filters the lists and returns the *indexes* of elements that satisfy the block. Further, `,` on a list zips it with its indices; instead, `L` computes the length of a list.
- In Paradoc, `R` joins sequences with other sequences and reduces/folds lists by a block, instead of `*`, which instead repeats a block over a list or the half-open range `[0..n)`, without pushing anything onto the stack, but instead putting each element into the special variable `X`. This allows `*` to behave consistently on integers `n` and half-open ranges `[0..n)`, and for it to perform the more intuitive Cartesian products on sequences.
- In Paradoc, `@` and `#` are changed to what I consider more mnemonic operations. `@` finds the index of an element or substring in a sequence (so it figures out where the element is **at**) and `#` counts the **number** of occurrences of that element of substring. Exponentiation is relegated to the (non-ASCII character) `ˆ` or `*p`, which seems a more reasonable mnemonic anyway (although I thought the audial mnemonic of **Pound** for `#` and **Power** was pretty reasonable) and allows it to also perform list exponentiation in the sense of Cartesian products. There is currently no one-character built-in for the stack-manipulation analogue of `@` in GolfScript/CJam.
- Most of the alphabetic built-ins are different, of course.
