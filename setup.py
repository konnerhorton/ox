"""Build the vendored tree-sitter grammar as the `ox._grammar` extension.

Package metadata lives in pyproject.toml; this file only declares the C
extension, compiled from the parser that `tree-sitter generate` writes to
tree-sitter-ox/src/.
"""

from setuptools import Extension, setup
from setuptools.command.build_ext import build_ext


class BuildExt(build_ext):
    def build_extension(self, ext: Extension):
        if self.compiler.compiler_type != "msvc":
            ext.extra_compile_args = ["-std=c11", "-fvisibility=hidden"]
        else:
            ext.extra_compile_args = ["/std:c11", "/utf-8"]
        super().build_extension(ext)


setup(
    ext_modules=[
        Extension(
            name="ox._grammar",
            sources=["src/ox/_grammar.c", "tree-sitter-ox/src/parser.c"],
            include_dirs=["tree-sitter-ox/src"],
            define_macros=[
                ("Py_LIMITED_API", "0x030C0000"),
                ("PY_SSIZE_T_CLEAN", None),
                ("TREE_SITTER_HIDE_SYMBOLS", None),
            ],
            py_limited_api=True,
        )
    ],
    cmdclass={"build_ext": BuildExt},
    options={"bdist_wheel": {"py_limited_api": "cp312"}},
)
