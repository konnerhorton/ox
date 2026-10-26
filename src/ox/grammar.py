"""The compiled tree-sitter grammar for .ox files.

The C parser is generated from `tree-sitter-ox/grammar.js` and built into
`ox._grammar` by the root `setup.py`.
"""

from tree_sitter import Language

from ox import _grammar

LANGUAGE = Language(_grammar.language())
