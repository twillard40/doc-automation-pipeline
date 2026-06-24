# Documentation Style Guide

## Document Structure

Every document must follow this order:

1. Title as H1
2. Summary section (H2) -- 2-3 sentences, no jargon, states what the doc covers and why it matters
3. Metadata block immediately after summary:
   - Ownership: [team name]
   - Last Reviewed: [date]
   - Keywords: [comma-separated tags for search/RAG discoverability]
4. Task-based sections (H2) -- each heading starts with "How to" (e.g., "How to Configure the Health Check")
5. Related Links section (H2) -- always last, includes tickets, specs, commits, upstream docs

## Headings

- H1: document title only, one per doc
- H2: major task sections and Related Links
- H3: subtasks or breakdowns within a section
- Never skip heading levels (no H1 to H3)
- Headings are task-based, not noun-based ("How to Verify Topology" not "Topology Verification")

## Voice and Tone

- Active voice throughout ("Run the script" not "The script should be run")
- Second person for instructions ("You can configure..." not "Users can configure...")
- Present tense for current behavior, past tense only for changelogs
- Direct and concise, no filler phrases ("Note that", "It is important to", "Please be aware")

## Terminology

- Define acronyms on first use: "earned run average (ERA)"
- After first definition, use the acronym only
- Use consistent terms across the doc (don't alternate between "endpoint" and "route")

## Warnings and Callouts

- Use markdown blockquote with bold label: > **Warning:** ...
- Reserve warnings for actions that can break things, cause data loss, or require elevated permissions
- Don't overuse -- more than two warnings per section dilutes their impact

## Code and Commands

- Wrap CLI commands, file paths, config keys, and endpoint paths in inline code
- Use fenced code blocks for multi-line commands or config examples
- Always specify the language after the opening fence (```bash, ```json, ```python)

## Tables

- Use tables for structured comparisons, parameter lists, or reference data
- Always include a header row
- Keep cell content short -- if it needs a paragraph, it belongs outside the table

## Lists

- Use numbered lists only for sequential steps
- Use bullet lists for non-ordered items
- Each list item is a complete thought, not a sentence fragment

## Sample Size and Data Caveats

- Flag when conclusions rest on limited data
- State the threshold explicitly ("Fewer than 50 at-bats")
- Don't present limited data as definitive
