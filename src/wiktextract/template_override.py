# Replacement functions that override specific templates,
# which should never be run as is because they cause problems.

# This dictionary should be assigned with the WTP.set_template_override()
# setter method; see wiktwords.
from collections.abc import Callable, Sequence


def _split_args(args: Sequence[str]) -> tuple[list[str], dict[str, str]]:
    positional: list[str] = []
    named: dict[str, str] = {}
    for arg in args:
        if "=" in arg:
            key, value = arg.split("=", 1)
            named[key.strip()] = value
        else:
            positional.append(arg)
    return positional, named

template_override_fns = {}

# https://stackoverflow.com/a/63071396
# To use parameters with reg() for the template-name stuff,
# we need to have three (four) levels of functions here.
# We do not technically have a wrapper function because
# we just return func as is. middle() is not a wrapper function,
# it's the actual decorator function itself (called with func)
# and reg() is actually a kind of wrapper around the decorator
# function that takes a parameter that middle() can't take.
# A bit messy conceptually.


def reg(template_name: str) -> Callable[[Callable], Callable]:
    """Decorator that takes its input key and the template it decorates,
    and adds them to the template_override_fns dictionary"""
    def middle(func: Callable) -> Callable:
        template_override_fns[template_name] = func
        return func
    return middle


@reg("egy-glyph")
def egy_glyph(args: Sequence[str]) -> str:
    """Intercept {{egy-glyph}}, which causes problems by creating
    tables and inserting agnostic images that can't be easily parsed
    as text data."""
    print(f"{args=}")
    ret = "EGY-GLYPH-ERROR"
    if "=" not in args[1]:
        ret = args[1]
    for arg in args[1:]:
        if "quad=" in arg:
            ret = arg[5:]
            ret = ret.replace("<br>", ":")
    return "«" + ret + "»"

@reg("egy-glyph-img")
def egy_glyph_img(args: Sequence[str]) -> str:
    """Intercept {{egy-glyph-img}}, which is turned into an inline
    image that is generally useless to our parser and replaces it
    with its egyptological code."""
    if "=" not in args[1]:
        return "«" + args[1] + "»"
    return "EGY-GLYPH-IMAGE-ERROR"


@reg("section link")
def section_link(args: Sequence[str]) -> str:
    """Provide a lightweight replacement for {{section link}}.

    The Lua implementation on Wiktionary primarily creates wikilinks to
    sections of policy or formatting pages.  The full Lua dependency tree is
    difficult to reproduce, so we generate a simplified link that preserves the
    target and human-readable label.
    """

    if len(args) <= 1:
        return ""

    positional, named = _split_args(args[1:])

    target = named.get("page") or named.get("1")
    if positional:
        target = positional[0]

    if not target:
        return ""

    section = named.get("section")
    display = named.get("display") or named.get("text")

    if len(positional) > 1 and section is None:
        section = positional[1]
    if len(positional) > 2 and not display:
        display = positional[2]

    if "#" in target:
        page_name, anchor = target.split("#", 1)
        if not section:
            section = anchor
        target = page_name
    elif named.get("anchor") and not section:
        section = named["anchor"]

    if section:
        link_target = f"{target}#{section}"
    else:
        link_target = target

    if not display:
        display = section or target
        if ":" in display:
            display = display.split(":", 1)[-1]

    display = display.strip()
    if not display:
        return f"[[{link_target}]]"

    return f"[[{link_target}|{display}]]"
