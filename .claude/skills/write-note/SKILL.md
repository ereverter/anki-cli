---
name: write-note
description: Guidelines for writing effective Anki flashcards. Use when creating, reviewing, or improving notes.
user-invocable: true
argument-hint: [topic or note content]
---

# Writing Good Anki Notes

Based on "An Opinionated Guide to Using Anki Correctly" by Luise Woehlke.

## Core Rules

### 1. Atomic cards — as short as possible
A typical card should have **no more than 9 words** on the back. One word is ideal. If a card can be split into two shorter cards, split it. Absolute maximum: 3 bullets / 18 words.

Bad: `"Greek letter τ" → "pronounced tau, used for time constants and torque"`
Good: Two cards — `"pronunciation τ" → "tau"` and `"τ in physics" → "time constant, torque"`

### 2. No to-be-learned info in the prompt
You only memorize the back. If the front contains crucial info (dates, names, context), you'll recall a disconnected fragment like "24%" with no idea what it refers to.

Bad: `"1950 Germany agriculture workforce %" → "24%"`
Good: `"agriculture in history" → "1950 Germany, 24% of workforce"`

### 3. Bland, standardized prompts
Eliminate memory shortcuts. No images, fancy formatting, unusual words, or cloze deletions in prompts. Standardize recurring prompt shapes:

| Instead of | Use |
|---|---|
| "When did X happen?" | `X dates` |
| "What's the term for X?" | `T X` |
| "What person did X?" | `who X` |
| "What is the definition of X?" | `X formally` |
| "What are the pros/cons of X?" | `X pros/cons` |

Avoid words in the prompt that also appear in the answer — they become shortcuts.

### 4. Match real-life prompts
The prompt should mirror the real situation where you'd want to recall the info. Usually the obvious prompt is too specific. Ask: "When will I actually need this?"

Bad: `"Length of whale intestine" → "..."` (when would you ever think this exact phrase?)
Good: `"animal fun facts" → "whale intestine is X meters long"`

### 5. Redundancy is good
- **Always make cards reversible** if it makes semantic sense
- Make **multiple cards** with different prompt formulations for the same fact
- Overlapping information across cards is a feature, not a bug

## Structuring Complex Information

### Handles (`>`)
Use `>topic` references to keep cards short while preserving connections. A handle points to another card with more detail.

```
"Isaac Newton contributions" → "laws of motion, >optics, >calculus"
"Newton optics" → "light is made of particles, color spectrum via prism"
```

### Levels
Break a topic into level 1 (overview) and level 2+ (detail) cards instead of cramming everything into one.

```
Level 1: "Galileo" → "astronomer ~1600, heliocentrism, telescope observations"
Level 2: "Galileo telescope" → "Jupiter moons, Venus phases, Moon craters"
```

Add a card to remember you have multiple levels: `"Galileo card count" → "2 levels"`.

### Trees over sequences
For information thickets (textbook sections, exam material), find a tree shape: root = main theme, branches = subquestions, leaves = details. Prefer **levels of abstraction** over sequential breakdowns (e.g., by year).

### Context cards
If you might forget what parent topic a card belongs to, make a context card:
`"Battle of Midway context" → "WW2 Pacific theater"`

It's fine to give context in the prompt of the detail card too — this makes it shorter to recall.

## When Creating Notes with anki-cli

When using `anki add` or `anki import` to create cards:

1. Split the material into atomic cards first — one concept per card
2. Use the Basic model for most cards; use "Basic (and reversed card)" when reversal makes sense
3. Tag related cards consistently so they can be found together via `anki search`
4. For handles, just write `>topic` in the field text — it's a reading convention, not Anki syntax
5. Keep new cards to ~2/day (with a 20-card daily review limit)

## What NOT to Ankify

Cards are expensive — each one is a long-term commitment to review. Start by only ankifying what you absolutely must know. Ruthlessly suspend cards that don't pay enough rent. You can always lower your bar later.

Consider the guidelines above to: $ARGUMENTS
