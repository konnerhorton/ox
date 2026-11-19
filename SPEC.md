# Ox — Product Spec

## What is ox?

A plain text training log format and toolchain.
Write workouts in a `.ox` text file, parse them into structured data, analyze progress over time.
Inspired by [Beancount](https://github.com/beancount/beancount) — plain text accounting, but for training.
Designed for tracking progress over years and decades, not just weeks and months.

## Who is it for?

People who train consistently over years and want to own their data.
Developers and power users comfortable with text files and CLIs.

## Core Principles

- **Plain text is the source of truth.** The `.ox` file is the canonical record. Everything else is derived.
- **No cloud, no accounts, no lock-in.** Your data is a text file on your filesystem.
- **Paper-like flexibility with software analytics.** As easy to write as a notebook, but parseable for real analysis.
- **Long-lived data.** A log written today should be readable in 20 years. Text outlasts apps.

## Current State

What's built, what's open and what's next: [`STATUS.md`](STATUS.md).

## Direction

### Richer analysis

- Cycle tracking — micro/meso/macro periodization
- Movement definitions feeding into analysis (e.g. grouping by movement tag)
- Derived units from the stored duration and distance — pace, speed, and work rate

### Better editor experience

- LSP hover info (movement definitions, recent history for a movement)
- LSP completions for session templates
- Snippets for common entry patterns

## Plugins

- **Every analysis feature is a plugin,** builtin or user. A plugin receives the parsed log and its database and
  returns a table, text or a plot.
- **One file registers one plugin.** `@plugin "<file>.py"` loads it, relative to the `.ox` file that holds it.
- **Plugins are configured from the log:** `@plugin "<name>" "<config>"`, or `@plugin "<file>.py" "<config>"` on the
  line that loads it. The config is a Python literal (it may span lines; inner strings use single quotes) that ox
  parses and the plugin interprets; ox checks only that it parses. The first config for a plugin wins. Settings live in
  the log, not beside it, so they travel with it and lint can check them.

## Non-Goals

- **Not a workout planner or coach.** Ox records and analyzes. It doesn't prescribe.
- **Not a web app or mobile app.** CLI tool and text format.
- **Not a social platform.** No sharing, leaderboards, or community features.
- **No proprietary format extensions.** The `.ox` format stays simple enough to read with no tooling.
