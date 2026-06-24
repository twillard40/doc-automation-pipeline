import os
import subprocess
import json
import sys
import glob
from dotenv import load_dotenv
import anthropic
from atlassian import Confluence
load_dotenv()

# ==========================================
# 1. CONFIGURATION
# ==========================================
CONFLUENCE_URL = os.environ.get("CONFLUENCE_URL")       # e.g. https://yourname.atlassian.net
CONFLUENCE_USER = os.environ.get("CONFLUENCE_USER")      # your email
CONFLUENCE_TOKEN = os.environ.get("CONFLUENCE_TOKEN")    # API token from id.atlassian.com
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

SPACE_KEY = os.environ.get("CONFLUENCE_SPACE", "ENG")
PARENT_PAGE_ID = os.environ.get("CONFLUENCE_PARENT_ID", "")

required_vars = {
    "CONFLUENCE_URL": CONFLUENCE_URL,
    "CONFLUENCE_USER": CONFLUENCE_USER,
    "CONFLUENCE_TOKEN": CONFLUENCE_TOKEN,
    "ANTHROPIC_API_KEY": ANTHROPIC_API_KEY,
}
missing = [k for k, v in required_vars.items() if not v]
if missing:
    print(f"Missing required env vars: {', '.join(missing)}")
    sys.exit(1)

confluence = Confluence(
    url=CONFLUENCE_URL,
    username=CONFLUENCE_USER,
    password=CONFLUENCE_TOKEN
)
ai_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


# ==========================================
# 2. SOURCE INGESTION (file-based)
# ==========================================
def gather_source_materials(sources_dir="sources"):
    """
    Reads all .md, .txt, and .json files from a local sources/ directory.
    Drop Jira exports, Slack snippets, commit logs, or API specs in there.
    """
    print(f"Gathering source files from {sources_dir}/...")

    if not os.path.isdir(sources_dir):
        print(f"No '{sources_dir}/' directory found. Creating it with a sample file.")
        os.makedirs(sources_dir, exist_ok=True)
        sample = {
            "jira_tickets": [
                "PROJ-101: Implement retry logic for upstream timeout",
                "Status: In Review"
            ],
            "slack_threads": [
                "Dave: 'Default timeout is 30s, needs sudo to change.'",
                "Elena: 'Agreed, document the config file path too.'"
            ],
            "git_commits": [
                "feat: add health-check endpoint",
                "fix: resolve connection pool leak on restart"
            ],
            "api_specs": [
                "POST /v1/health/verify",
                "Headers: Authorization: Bearer <token>",
                "Returns: 200 OK or 503 Service Unavailable"
            ]
        }
        sample_path = os.path.join(sources_dir, "sample_input.json")
        with open(sample_path, "w", encoding="utf-8") as f:
            json.dump(sample, f, indent=2)
        print(f"  Created {sample_path} as starter input.")

    collected = []
    for pattern in ["*.md", "*.txt", "*.json"]:
        for filepath in sorted(glob.glob(os.path.join(sources_dir, pattern))):
            print(f"  Reading: {filepath}")
            with open(filepath, "r", encoding="utf-8") as f:
                collected.append(f"--- Source: {os.path.basename(filepath)} ---\n{f.read()}")

    if not collected:
        print("No source files found. Add .md, .txt, or .json files to sources/.")
        sys.exit(1)

    return "\n\n".join(collected)


# ==========================================
# 3. LLM DRAFT GENERATION
# ==========================================
def generate_draft(source_data, doc_title="Technical Documentation Draft"):
    """Generates a structured Markdown draft via Claude Haiku."""
    print("Generating Markdown draft via Claude...")

    prompt = f"""You are an expert technical writer at an infrastructure company.
Using the raw source data below, write a comprehensive internal technical documentation draft in Markdown.

STRUCTURE REQUIREMENTS:
1. Start with '# {doc_title}' followed by a '## Summary' section.
2. Include a metadata block: 'Ownership: [Team]', 'Last Reviewed: [today]', 'Keywords: [tags]'.
3. Use task-based headings (e.g., '## How to Verify the Health Check').
4. End with a '## Related Links' section.

STYLE:
- Active voice throughout.
- Define acronyms on first use.
- Use markdown admonitions for warnings (> **Warning:** ...).

RAW SOURCE DATA:
{source_data}"""

    response = ai_client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}]
    )

    draft_content = response.content[0].text

    output_path = "temp_draft.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(draft_content)

    print(f"  Draft saved to {output_path}")
    return output_path


# ==========================================
# 4. VALE LINTING
# ==========================================
def run_vale_linter(file_path):
    """Runs Vale CLI for style guide compliance. JSON output for downstream use."""
    print("Running Vale style linting...")
    try:
        result = subprocess.run(
            ["vale", "--output=JSON", file_path],
            capture_output=True,
            text=True,
            check=False
        )
        if not result.stdout.strip():
            print("  Vale returned no output. Skipping.")
            return
        violations = json.loads(result.stdout)
        if violations:
            total = sum(len(v) for v in violations.values())
            print(f"  Vale found {total} issue(s). Writer review recommended.")
        else:
            print("  Vale: no issues found.")
    except FileNotFoundError:
        print("  Vale CLI not found. Skipping lint. (pip install vale or brew install vale)")


# ==========================================
# 5. RETRIEVAL OPTIMIZATION VALIDATION
# ==========================================
def validate_retrieval_fields(file_path):
    """Checks that the draft includes fields needed for internal search/RAG discoverability."""
    print("Validating retrieval optimization fields...")
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read().lower()

    checks = {
        "Summary section":   "## summary" in content,
        "Ownership field":   "ownership:" in content,
        "Last Reviewed date": "last reviewed:" in content,
        "Keywords/Tags":     "keywords:" in content,
        "Related Links":     "## related links" in content,
    }

    all_passed = True
    for label, passed in checks.items():
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {label}")
        if not passed:
            all_passed = False

    return all_passed


# ==========================================
# 6. MARKDOWN TO CONFLUENCE XHTML + EXPORT
# ==========================================
def convert_to_confluence_xhtml(file_path):
    """Converts Markdown to Confluence Storage Format with automation notice."""
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    notice = (
        '<ac:structured-macro ac:name="info" ac:schema-version="1">'
        '<ac:rich-text-body><p><strong>AUTOMATED DRAFT</strong> '
        'Generated by doc_generator.py. Review before publishing.</p>'
        '</ac:rich-text-body></ac:structured-macro>'
    )

    xhtml = notice
    for line in lines:
        stripped = line.rstrip()
        if stripped.startswith("# "):
            xhtml += f"<h1>{stripped[2:]}</h1>"
        elif stripped.startswith("## "):
            xhtml += f"<h2>{stripped[3:]}</h2>"
        elif stripped.startswith("### "):
            xhtml += f"<h3>{stripped[4:]}</h3>"
        elif stripped.startswith("- "):
            xhtml += f"<ul><li>{stripped[2:]}</li></ul>"
        elif stripped.startswith("```"):
            continue  # skip fences for now
        elif stripped:
            xhtml += f"<p>{stripped}</p>"

    return xhtml


def export_to_confluence(title, html_content):
    """Creates or updates a page in Confluence."""
    print(f"Exporting to Confluence space '{SPACE_KEY}'...")

    try:
        if confluence.page_exists(SPACE_KEY, title):
            page_id = confluence.get_page_id(SPACE_KEY, title)
            print(f"  Updating existing page (ID: {page_id})...")
            kwargs = {
                "page_id": page_id,
                "title": title,
                "body": html_content,
                "type": "page",
                "representation": "storage",
            }
            if PARENT_PAGE_ID:
                kwargs["parent_id"] = PARENT_PAGE_ID
            confluence.update_page(**kwargs)
        else:
            print("  Creating new page...")
            kwargs = {
                "space": SPACE_KEY,
                "title": title,
                "body": html_content,
                "type": "page",
                "representation": "storage",
            }
            if PARENT_PAGE_ID:
                kwargs["parent_id"] = PARENT_PAGE_ID
            confluence.create_page(**kwargs)

        print("  Export complete. Page ready for review.")
    except Exception as e:
        print(f"  Confluence export failed: {e}")
        sys.exit(1)


# ==========================================
# MAIN
# ==========================================
if __name__ == "__main__":
    doc_title = sys.argv[1] if len(sys.argv) > 1 else "Technical Documentation Draft"
    print(f"--- Doc Pipeline: '{doc_title}' ---\n")

    # 1. Ingest
    raw = gather_source_materials()

    # 2. Generate
    draft_path = generate_draft(raw, doc_title)

    # 3. Lint
    run_vale_linter(draft_path)

    # 4. Validate retrieval fields
    validate_retrieval_fields(draft_path)

    # 5. Convert and export
    xhtml = convert_to_confluence_xhtml(draft_path)
    export_to_confluence(f"[DRAFT] {doc_title}", xhtml)

    # Cleanup
    if os.path.exists(draft_path):
        os.remove(draft_path)

    print("\n--- Pipeline complete ---")