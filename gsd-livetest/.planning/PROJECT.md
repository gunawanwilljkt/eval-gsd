# Project: slugify-lib

**Created:** 2026-06-01
**Status:** Active

## Vision

A tiny, dependency-free Node ESM utility that turns arbitrary text into URL-safe slugs.

## Core Value

`slugify(text)` produces clean, predictable slugs: lowercased, trimmed, runs of
non-alphanumeric characters collapsed to a single hyphen, no leading/trailing hyphens.

## Scope

- In: a single exported `slugify(text)` function in an ESM module.
- Out: configurability, i18n/transliteration, CLI, packaging/publishing.
