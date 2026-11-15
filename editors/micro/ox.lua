-- Ox training log support for micro: syntax highlighting for .ox files.
VERSION = "0.1.0"

local config = import("micro/config")

-- Registered in preinit(), which micro calls before it opens any buffer, so a
-- file named on the command line is highlighted from the first frame.
function preinit()
    config.AddRuntimeFile("ox", config.RTSyntax, "syntax/ox.yaml")
    config.AddRuntimeFile("ox", config.RTHelp, "help/ox.md")
end
