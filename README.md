# doc-automation-pipeline
Automates doc drafts in github for confluence
# Doc Automation Pipeline

A Python pipeline that ingests raw engineering artifacts (Jira exports, Slack threads, commit logs, API specs), generates structured technical documentation via LLM, validates it for search and retrieval optimization, and exports it directly to Confluence as a draft page.

Built to demonstrate docs-as-code automation for internal documentation workflows at engineering organizations.

## Pipeline Stages

```
sources/            Claude Haiku           Vale CLI          Confluence API
┌──────────┐      ┌──────────────┐      ┌───────────┐      ┌──────────────┐
│  Ingest  │ ───▸ │   Generate   │ ───▸ │  Validate │ ───▸ │    Export    │
│          │      │              │      │           │      │              │
│ .md .txt │      │ Structured   │      │ Style     │      │ XHTML draft  │
│ .json    │      │ Markdown     │      │ Retrieval │      │ Create or    │
│          │      │ draft        │      │ fields    │      │ update page  │
└──────────┘      └──────────────┘      └───────────┘      └──────────────┘
```

**Ingest** -- Reads all `.md`, `.txt`, and `.json` files from a local `sources/` directory. Drop in Jira exports, Slack threads, git logs, design docs, or API specs.

**Generate** -- Sends combined source material to Claude Haiku 4.5 with a structured prompt template. Output follows task-based headings, includes metadata fields (ownership, review date, keywords), and uses active voice.

**Validate** -- Runs two checks before export:
- Vale CLI for style guide compliance (JSON output, parseable for LLM feedback loops)
- Retrieval optimization gate: verifies the draft includes summary, ownership, review date, keywords, and related links sections required for internal search and RAG discoverability

**Export** -- Converts Markdown to Confluence Storage Format (XHTML) with an automation notice macro, then creates or updates the page via the Confluence REST API. Handles idempotent updates (won't duplicate pages on re-runs).

## Sample Output

The pipeline generates structured Confluence pages from raw engineering artifacts:

![Confluence output](docs/confluence-output.png)

*Generated from a project README, Jira tickets, Slack threads, and git commit logs.*

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
pip install anthropic atlassian-python-api python-dotenv
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
```

## Usage

Add source files to the `sources/` directory, then run:

```bash
python doc_generator.py "Your Document Title"
```

The pipeline reads all sources, generates a draft, validates it, and exports a page titled `[DRAFT] Your Document Title` to your Confluence space.

First run with no `sources/` directory creates a sample input file automatically.

## Tech Stack

- **LLM**: Claude Haiku 4.5 via Anthropic API
- **Agent framework**: Compatible with [smolagents](https://github.com/huggingface/smolagents) for tool-calling agent integration
- **Linting**: Vale CLI (JSON output for programmatic feedback)
- **CMS**: Confluence Cloud (REST API via atlassian-python-api)
- **Config**: python-dotenv for credential management

## Architecture Decisions

**Why file-based ingestion**: Avoids API auth complexity for each source system while keeping the pipeline functional against real data. Source integrations (Jira API, Slack API, `git log`) can be added incrementally without changing the pipeline stages.

**Why a retrieval validation gate**: Internal docs are only useful if they're findable. The validation stage checks for metadata fields that internal search engines and RAG systems depend on (summary, ownership, keywords, review dates). Documents that fail the gate need manual remediation before export.

**Why Confluence Storage Format**: Direct XHTML export with Confluence macros (info panels, structured markup) produces pages that render correctly without manual formatting. The automation notice macro flags every generated page as a draft requiring human review.

## Roadmap

- [ ] Robust Markdown-to-XHTML converter (lists, code blocks, tables)
- [ ] Live source ingestion (Jira REST API, `git log`, Slack API)
- [ ] Vale violation feedback loop (pass lint errors back to LLM for self-correction)
- [ ] Agent-driven ingestion via smolagents ToolCallingAgent
- [ ] Multi-document batch generation

## License

MIT