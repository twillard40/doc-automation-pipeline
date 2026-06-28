# Doc Automation Pipeline

A Python pipeline that ingests engineering artifacts from multiple sources (local files, live Jira tickets, source code), generates structured technical documentation via LLM guided by an external style guide, validates it for search and retrieval optimization, and exports it directly to Confluence as a draft page.

Built to demonstrate docs-as-code automation for internal documentation workflows at engineering organizations.

## Pipeline Stages

```
sources/ + Jira     Claude Haiku           Vale CLI          Confluence API
┌──────────┐      ┌──────────────┐      ┌───────────┐      ┌──────────────┐
│  Ingest  │ ───▸ │   Generate   │ ───▸ │  Validate │ ───▸ │    Export    │
│          │      │              │      │           │      │              │
│ .md .txt │      │ Style guide  │      │ Style     │      │ XHTML draft  │
│ .json .py│      │ loaded at    │      │ Retrieval │      │ Create or    │
│ Jira v3  │      │ runtime      │      │ fields    │      │ update page  │
└──────────┘      └──────────────┘      └───────────┘      └──────────────┘
```

**Ingest** -- Reads `.md`, `.txt`, `.json`, and `.py` files from a local `sources/` directory, plus pulls live Jira tickets via configurable JQL query. Drop in READMEs, design docs, commit logs, API specs, or source code. The pipeline reads code and generates documentation from it.

**Generate** -- Loads `style_guide.md` at runtime and sends it alongside combined source material to Claude Haiku 4.5. The style guide controls output structure, heading conventions, voice, terminology, and formatting. Change the guide, the output changes -- no code edits needed.

**Validate** -- Runs two checks before export:
- Vale CLI for style guide compliance (JSON output, parseable for LLM feedback loops)
- Retrieval optimization gate: verifies the draft includes summary, ownership, review date, keywords, and related links sections required for internal search and RAG discoverability

**Export** -- Converts Markdown to Confluence Storage Format (XHTML) using the `markdown` library with extensions for tables, fenced code blocks, and proper list nesting. Code blocks render in Confluence code macros. Every page includes an automation notice macro flagging it as a draft requiring human review. Handles idempotent updates (won't duplicate pages on re-runs).

## Sample Output

The pipeline generates structured Confluence pages from raw engineering artifacts:

![Confluence output](docs/confluence-output.png)

*Generated from a project README, Jira tickets, and Python source code.*

## Setup

### Prerequisites

- Python 3.10+
- A Confluence Cloud instance with an API token ([generate one here](https://id.atlassian.com/manage-profile/security/api-tokens))
- An Anthropic API key ([get one here](https://console.anthropic.com/))
- (Optional) [Vale CLI](https://vale.sh/) for style linting

### Install

```bash
git clone https://github.com/twillard40/doc-automation-pipeline.git
cd doc-automation-pipeline
pip install anthropic atlassian-python-api python-dotenv markdown
```

### Configure

Create a `.env` file in the project root:

```
ANTHROPIC_API_KEY=sk-ant-xxxxx
CONFLUENCE_URL=https://yourinstance.atlassian.net
CONFLUENCE_USER=you@email.com
CONFLUENCE_TOKEN=your-api-token
CONFLUENCE_SPACE=ENG
CONFLUENCE_PARENT_ID=optional-parent-page-id
JIRA_JQL=project = KAN AND labels = "docs-ready" ORDER BY created DESC
```

The `JIRA_JQL` variable accepts any valid JQL query. This controls which tickets the pipeline pulls -- filter by project, status, labels, date range, or any combination. Examples:

- `project = KAN AND labels = "docs-ready"` -- only tickets flagged for documentation
- `project = KAN AND status = "Done" AND resolved >= -7d` -- tickets closed in the last week
- `project = KAN AND labels IN ("docs-ready", "bug", "api-change")` -- multiple label filters

## Usage

Add source files to the `sources/` directory, then run:

```bash
python doc_generator.py "Your Document Title"
```

The pipeline reads all sources, pulls matching Jira tickets, generates a draft, validates it, and exports a page titled `[DRAFT] Your Document Title` to your Confluence space.

First run with no `sources/` directory creates a sample input file automatically.

### Style Guide

The file `style_guide.md` in the project root controls how Claude structures and writes the output. It defines heading conventions, voice, terminology rules, callout formatting, and more. Edit it to match your organization's documentation standards -- the pipeline loads it fresh on every run.

## Tech Stack

- **LLM**: Claude Haiku 4.5 via Anthropic API
- **Source ingestion**: Local files (`.md`, `.txt`, `.json`, `.py`) + Jira v3 REST API with JQL filtering
- **Style control**: External `style_guide.md` loaded at runtime
- **Markdown conversion**: `markdown` library with tables, fenced code, and sane lists extensions
- **Linting**: Vale CLI (JSON output for programmatic feedback)
- **CMS**: Confluence Cloud (REST API via atlassian-python-api)
- **Config**: python-dotenv for credential management

## Architecture Decisions

**Why a configurable JQL filter**: The pipeline doesn't pull every ticket in a project. A JQL query in the `.env` file controls which tickets feed into the doc. Teams can filter by label (`docs-ready`), status (`Done`), date range, or any Jira field. This makes the intake intentional rather than a firehose.

**Why an external style guide**: Hardcoding output rules in the prompt means editing Python to change doc formatting. Loading `style_guide.md` at runtime separates editorial decisions from pipeline code. A tech writer can update the guide without touching the script.

**Why a retrieval validation gate**: Internal docs are only useful if they're findable. The validation stage checks for metadata fields that internal search engines and RAG systems depend on (summary, ownership, keywords, review dates). Documents that fail the gate need manual remediation before export.

**Why Confluence Storage Format**: Direct XHTML export with Confluence macros (info panels, code blocks, structured markup) produces pages that render correctly without manual formatting. The automation notice macro flags every generated page as a draft requiring human review.

## Roadmap

- [ ] Vale violation feedback loop (pass lint errors back to LLM for self-correction)
- [ ] Agent-driven ingestion via smolagents ToolCallingAgent
- [ ] Google Docs API integration for live doc pulls
- [ ] Git log integration (auto-pull recent commits as source material)
- [ ] Multi-document batch generation

## License

MIT
