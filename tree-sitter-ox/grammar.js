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
      $.template_block
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

    // @session block
    session_block: ($) =>
      seq(
        "@session",
        "\n",
        field("date", $.date),
        field("flag", $.flag),
        field("name", $.name),
        "\n",
        repeat($.item_line),
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
        repeat($.item_line),
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
    // TODO: standalone notes should require quotes for consistency
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
    
    // TODO: should have any mass measurement from Python's pint available here. not just kg and lbs
    weight: ($) => token(choice(
      /\d+(kg|lbs)((\+\d+(kg|lbs))+)?/,  // 24kg or 24kg+32kg+48kg
      /\d+(kg|lbs)((\/\d+(kg|lbs))+)?/,  // 24kg or 24kg/32kg/48kg
      /BW/                                // bodyweight
    )),

    rep_scheme: ($) => /(\d+x\d+)|(\d+(\/\d+)+)/,  // 4x4 or 5/5/5

    time: ($) => /\d+(sec|min|hr)/,

    distance: ($) => /\d+(km|mi|m|ft|in)/,

    quoted_string: ($) => /"[^"]*"/,
  },
});
