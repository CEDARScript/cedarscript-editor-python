# # Credits
# 
# CEDARScript uses modified versions of the tags.scm files from these open source
# tree-sitter language implementations:
# 
# * [https://github.com/tree-sitter/tree-sitter-c](https://github.com/tree-sitter/tree-sitter-c) — licensed under the MIT License.
# * [https://github.com/tree-sitter/tree-sitter-c-sharp](https://github.com/tree-sitter/tree-sitter-c-sharp) — licensed under the MIT License.
# * [https://github.com/tree-sitter/tree-sitter-cpp](https://github.com/tree-sitter/tree-sitter-cpp) — licensed under the MIT License.
# * [https://github.com/Wilfred/tree-sitter-elisp](https://github.com/Wilfred/tree-sitter-elisp) — licensed under the MIT License.
# * [https://github.com/elixir-lang/tree-sitter-elixir](https://github.com/elixir-lang/tree-sitter-elixir) — licensed under the Apache License, Version 2.0.
# * [https://github.com/elm-tooling/tree-sitter-elm](https://github.com/elm-tooling/tree-sitter-elm) — licensed under the MIT License.
# * [https://github.com/tree-sitter/tree-sitter-go](https://github.com/tree-sitter/tree-sitter-go) — licensed under the MIT License.
# * [https://github.com/tree-sitter/tree-sitter-java](https://github.com/tree-sitter/tree-sitter-java) — licensed under the MIT License.
# * [https://github.com/tree-sitter/tree-sitter-javascript](https://github.com/tree-sitter/tree-sitter-javascript) — licensed under the MIT License.
# * [https://github.com/tree-sitter/tree-sitter-ocaml](https://github.com/tree-sitter/tree-sitter-ocaml) — licensed under the MIT License.
# * [https://github.com/tree-sitter/tree-sitter-php](https://github.com/tree-sitter/tree-sitter-php) — licensed under the MIT License.
# * [https://github.com/tree-sitter/tree-sitter-python](https://github.com/tree-sitter/tree-sitter-python) — licensed under the MIT License.
# * [https://github.com/tree-sitter/tree-sitter-ql](https://github.com/tree-sitter/tree-sitter-ql) — licensed under the MIT License.
# * [https://github.com/r-lib/tree-sitter-r](https://github.com/r-lib/tree-sitter-r) — licensed under the MIT License.
# * [https://github.com/tree-sitter/tree-sitter-ruby](https://github.com/tree-sitter/tree-sitter-ruby) — licensed under the MIT License.
# * [https://github.com/tree-sitter/tree-sitter-rust](https://github.com/tree-sitter/tree-sitter-rust) — licensed under the MIT License.
# * [https://github.com/tree-sitter/tree-sitter-typescript](https://github.com/tree-sitter/tree-sitter-typescript) — licensed under the MIT License.

# query_scm = get_scm_fname(langstr)
# query_scm = query_scm.read_text()
# def get_scm_fname(langstr):
#     # Load the tags queries
#     try:
#         return resources.files(__package__).joinpath("queries", f"tree-sitter-{langstr}-tags.scm")
#     except KeyError:
#         return

from importlib.resources import files

_tree_sitter_queries = files("tree-sitter-queries")


def get_query(langstr: str) -> dict[str, str]:
    basedir = _tree_sitter_queries / langstr
    if not basedir.exists():
        raise KeyError(f"Missing language dir: {basedir}")
    base_template = (basedir / "basedef.scm").read_text(encoding='utf-8')
    common_template = (basedir / "common.scm").read_text(encoding='utf-8')
    templates2 = {
        "function": (basedir / "functions.scm").read_text(encoding='utf-8'),
        "class": (basedir / "classes.scm").read_text(encoding='utf-8')
    }
    return {
        _type: templates2[_type].format(
            definition_base=base_template.format(type=_type),
            common_body=common_template.format(type=_type)
        )
        for _type in ["function", "class"]
    }
