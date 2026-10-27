# docgx, for AI agents

A person pointed you here. `docgx` checks that a page or slide actually fits
before anyone presents it: declare a title and positioned text blocks as a
Python file, then `docgx inspect` measures them exactly as it renders them and
reports text that runs off the page or out of its card, covers other text, is too
small, or breaks the word budget — plus a storyboard with the evidence.

A block may declare the column or card it lives in with `width` / `height`
(fractions of the page). Use them on any page that is not one column, and on any
card whose text has to fit: without `width` every block wraps at the page width,
so a two-column page is measured as something the reader never sees.

This tool is part of `gxkit`; the review contract (`inspect`, `--json`, exit
codes, storyboard) is shared with every other tool in the family.

## Set it up

```sh
uvx --from "git+https://github.com/nekomario28/gxkit#subdirectory=packages/docgx" docgx --help
# or, from a clone:
uv tool install ./packages/docgx    # puts `docgx` on PATH
```

## The loop

1. **Write** the page as a `.py` file that builds a `Page` (or defines
   `TITLE` / `BLOCKS` / `WIDTH` / `HEIGHT` / `MAX_WORDS`).
2. **Inspect** — `docgx inspect page.py`. Prints the page summary, every problem
   with a stable `code`, and writes `<name>.storyboard.png`.
   **Exit code 1 means at least one error.**
3. **Fix** the `error` and `warn` problems, inspect again. Look at the storyboard
   if you can view images — each numbered box proves a problem.
4. **Render** — `docgx render page.py -o page.png`.

## Reading the report

- `error` — `clipped-text` (runs off the page edge), `text-overflow` (runs out of
  the `width`/`height` box it declares — a column, or a card), `text-overlap` (two
  blocks cover each other).
- `warn` — `no-title`, `too-much-text` (over the declared `max_words`).
- `info` — `small-text` (below the readable floor), `reading-order` (blocks are
  declared out of top-to-bottom order), `empty-page`.

Common fixes: `clipped-text` → shorten the text or lower `font_size`;
`text-overflow` → give the block a taller `height`, a wider `width`, or less text;
`text-overlap` → move a block (`x`/`y` are fractions of the page);
`small-text` → raise `font_size`; `too-much-text` → raise `max_words` or cut
words. The layout checks are the same code `chartgx` uses. Use `--json` to branch
on the result.
