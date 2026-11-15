# Ox

This plugin adds syntax highlighting for Ox training logs, the plain-text files
with the `.ox` extension that the `ox` command reads.

Colors come from your colorscheme. The plugin uses these groups:

* `comment`: comments
* `preproc`: `@session`, `@end`, `@movement`, `@template`, `@include`, `@plugin`
* `statement`: the `T`, `W`, `note` and `query` markers, and field keys such as
  `date:` and `srpe:`
* `type`: dates and session names
* `special`: movement names
* `identifier`: rep schemes such as `5x5` and `5/5/5`
* `constant.number`: weights, distances, durations and sRPE ratings
* `constant.bool`: the value of `completed:`
* `constant.string`: quoted strings

The file format and the `ox` command are documented at
https://konnerhorton.github.io/ox
