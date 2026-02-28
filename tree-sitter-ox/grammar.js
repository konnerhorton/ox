/**
 * @file Parse training logs.
 * @author konnerhorton <konnerhorton@gmail.com>
 * @license MIT
 */

/// <reference types="tree-sitter-cli/dsl" />
// @ts-check

module.exports = grammar({
  name: "ox",

  extras: ($) => [/[ \t]/], // Only spaces and tabs, NOT newlines

  rules: {
    source_file: ($) => repeat(choice($._entry, $.comment, "\n")),

    _entry: ($) => choice(
      $.singleline_entry,
      $.session_block,
      $.exercise_block,
      $.template_block,
      $.note_entry,
      $.query_entry
    ),

    comment: ($) => /#[^\n]*/,

    // Single-line entry: date flag item: details
    singleline_entry: ($) =>
      seq(
        field("date", $.date),
        field("flag", $.flag),
        field("item", $.item),
        ":",
        optional(field("details", $.details)),
        "\n"
      ),

    // Standalone note entry: date note "text"
    note_entry: ($) =>
      seq(
        field("date", $.date),
        "note",
        field("text", $.quoted_string),
        "\n"
      ),

    // Query entry: date query "name" "SQL"
    query_entry: ($) =>
      seq(
        field("date", $.date),
        "query",
        field("name", $.quoted_string),
        field("sql", $.quoted_string),
        "\n"
      ),

    // @session block
    session_block: ($) =>
      seq(
        "@session",
        "\n",
        field("date", $.date),
        field("flag", $.flag),
        field("name", $.name),
        "\n",
        repeat(choice($.item_line, $.note_line)),
        "@end",
        "\n"
      ),

    // @exercise block
    exercise_block: ($) =>
      seq(
        "@exercise",
        field("name", $.identifier),
        "\n",
        repeat($.metadata_line),
        "@end",
        "\n"
      ),

    // @template block
    template_block: ($) =>
      seq(
        "@template",
        field("name", $.name),
        "\n",
        repeat(choice($.item_line, $.note_line)),
        "@end",
        "\n"
      ),

    // Item line within a block: item: details
    item_line: ($) =>
      seq(
        field("item", $.item),
        ":",
        field("details", $.details),
        "\n"
      ),

    // Note line within a session/template block: note: "text"
    note_line: ($) =>
      seq(
        "note:",
        field("text", $.quoted_string),
        "\n"
      ),

    // Metadata line within definition blocks: key: value
    metadata_line: ($) =>
      seq(
        field("key", $.identifier),
        ":",
        optional(field("value", $.text_until_newline)),
        "\n"
      ),

    date: ($) => /\d{4}-\d{2}-\d{2}/,

    flag: ($) => choice("*", "!", "W"),

    // Item name (before colon)
    item: ($) => /[^\s:]+/,

    // Identifier (exercise names, metadata keys)
    identifier: ($) => /[^\s:]+/,

    // Name (session/template names, extends to newline, no quotes)
    name: ($) => /[^\n]+/,

    // Text until newline (for metadata values, standalone notes)
    text_until_newline: ($) => /[^\n]+/,

    // Details: combination of weights, reps, time, distance, quoted notes
    details: ($) =>
      repeat1(
        choice(
          field("weight", $.weight),
          field("rep_scheme", $.rep_scheme),
          field("time", $.time),
          field("distance", $.distance),
          field("note", $.quoted_string)
        )
      ),

    // Mass units: curated from pint's default_en.txt
    // Breaking change: lbs → lb (pint's official symbol)
    // BW remains a special bodyweight token
    weight: ($) => token(choice(
      /\d+(\.\d+)?(g|gram|kg|kilogram|lb|pound|oz|ounce|stone|t|tonne|grain|gr|ct|carat)((\+\d+(\.\d+)?(g|gram|kg|kilogram|lb|pound|oz|ounce|stone|t|tonne|grain|gr|ct|carat))+)?/,  // single or combined: 24kg or 24kg+32kg
      /\d+(\.\d+)?(g|gram|kg|kilogram|lb|pound|oz|ounce|stone|t|tonne|grain|gr|ct|carat)((\/\d+(\.\d+)?(g|gram|kg|kilogram|lb|pound|oz|ounce|stone|t|tonne|grain|gr|ct|carat))+)?/,  // single or progressive: 24kg/32kg/48kg
      /BW/                                // bodyweight
    )),

    rep_scheme: ($) => /(\d+x\d+)|(\d+(\/\d+)+)/,  // 4x4 or 5/5/5

    // Time units: curated from pint's default_en.txt
    time: ($) => /\d+(\.\d+)?(s|sec|second|min|minute|h|hr|hour|d|day|week|month|yr|year)/,

    // Distance units: curated from pint's default_en.txt
    distance: ($) => /\d+(\.\d+)?(m|meter|metre|km|kilometer|cm|centimeter|mm|millimeter|in|inch|ft|foot|yd|yard|mi|mile|nmi)/,

    quoted_string: ($) => /"[^"]*"/,
  },
});
