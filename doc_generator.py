import os
import subprocess
import json
import sys
import glob
import requests
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
JIRA_JQL = os.environ.get("JIRA_JQL", "")

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


def gather_jira_tickets(jql_query):
    """Pulls tickets from Jira using a configurable JQL query via the v3 REST API."""
    print(f"Pulling Jira tickets (JQL: {jql_query})...")

    try:
        url = f"{CONFLUENCE_URL}/rest/api/3/search/jql"
        params = {
            "jql": jql_query,
            "maxResults": 25,
            "fields": "summary,status,priority,issuetype,description,labels"
        }
        resp = requests.get(
            url,
            params=params,
            auth=(CONFLUENCE_USER, CONFLUENCE_TOKEN)
        )
        resp.raise_for_status()
        issues = resp.json().get("issues", [])

        if not issues:
            print("  No tickets found.")
            return ""

        ticket_lines = []
        for issue in issues:
            key = issue["key"]
            fields = issue["fields"]
            summary = fields.get("summary", "No summary")
            status = fields.get("status", {}).get("name", "Unknown")
            priority = fields.get("priority", {}).get("name", "None")
            issue_type = fields.get("issuetype", {}).get("name", "Task")
            labels = ", ".join(fields.get("labels", [])) or "None"

            # v3 API returns description as Atlassian Document Format (JSON)
            desc_field = fields.get("description")
            if desc_field and isinstance(desc_field, dict):
                # Extract text from ADF content nodes
                desc_parts = []
                for block in desc_field.get("content", []):
                    for inline in block.get("content", []):
                        if inline.get("type") == "text":
                            desc_parts.append(inline.get("text", ""))
                description = " ".join(desc_parts) or "No description provided."
            else:
                description = "No description provided."

            ticket_lines.append(
                f"### {key}: {summary}\n"
                f"- Type: {issue_type}\n"
                f"- Status: {status}\n"
                f"- Priority: {priority}\n"
                f"- Labels: {labels}\n"
                f"- Description: {description}\n"
            )

        print(f"  Pulled {len(issues)} ticket(s).")
        return f"--- Source: Jira ({jql_query}) ---\n" + "\n".join(ticket_lines)

    except Exception as e:
        print(f"  Jira pull failed: {e}")
        return ""


# ==========================================
# 3. LLM DRAFT GENERATION
# ==========================================
def load_style_guide(style_guide_path="style_guide.md"):
    """Loads the style guide from disk. Returns empty string if not found."""
    if not os.path.isfile(style_guide_path):
        print(f"  No style guide found at {style_guide_path}. Using defaults.")
        return ""
    with open(style_guide_path, "r", encoding="utf-8") as f:
        return f.read()


def generate_draft(source_data, doc_title="Technical Documentation Draft"):
    """Generates a structured Markdown draft via Claude Haiku, guided by style_guide.md."""
    print("Generating Markdown draft via Claude...")

    style_guide = load_style_guide()

    prompt = f"""You are an expert technical writer at an infrastructure company.
Using the raw source data below, write a comprehensive internal technical documentation draft in Markdown.

The document title is: {doc_title}

STYLE GUIDE (follow strictly):
{style_guide}

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
    """Converts Markdown to Confluence Storage Format using the markdown library."""
    import markdown

    with open(file_path, "r", encoding="utf-8") as f:
        md_text = f.read()

    # Convert markdown to HTML with extensions for tables, code blocks, etc.
    html_body = markdown.markdown(
        md_text,
        extensions=["tables", "fenced_code", "nl2br", "sane_lists"]
    )

    # Wrap code blocks in Confluence code macro for proper rendering
    html_body = html_body.replace(
        "<code>",
        '<code>'
    ).replace(
        "<pre>",
        '<ac:structured-macro ac:name="code" ac:schema-version="1">'
        '<ac:plain-text-body><![CDATA['
    ).replace(
        "</pre>",
        ']]></ac:plain-text-body></ac:structured-macro>'
    )

    notice = (
        '<ac:structured-macro ac:name="info" ac:schema-version="1">'
        '<ac:rich-text-body><p><strong>AUTOMATED DRAFT</strong> '
        'Generated by doc_generator.py. Review before publishing.</p>'
        '</ac:rich-text-body></ac:structured-macro>'
    )

    return notice + html_body


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

    # 1b. Pull Jira tickets if JQL query is configured
    if JIRA_JQL:
        jira_data = gather_jira_tickets(JIRA_JQL)
        if jira_data:
            raw = raw + "\n\n" + jira_data

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
