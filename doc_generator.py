import os
import subprocess
import json
import sys
from atlassian import Confluence
from openai import OpenAI

# ==========================================
# 1. CONFIGURATION & CONFIG MANAGEMENT
# ==========================================
CONFLUENCE_URL = os.environ.get("CONFLUENCE_URL", "https://your-domain.atlassian.net")
CONFLUENCE_USER = os.environ.get("CONFLUENCE_USER")
CONFLUENCE_TOKEN = os.environ.get("CONFLUENCE_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# Target location for the documentation
SPACE_KEY = "ENG"
PARENT_PAGE_ID = "123456789"  # Nest under the correct project tree

# Initialize Clients
if not all([CONFLUENCE_USER, CONFLUENCE_TOKEN, OPENAI_API_KEY]):
    print("❌ Error: Missing required environment variables.")
    sys.exit(1)

confluence = Confluence(url=CONFLUENCE_URL, username=CONFLUENCE_USER, password=CONFLUENCE_TOKEN)
ai_client = OpenAI(api_key=OPENAI_API_KEY)

# ==========================================
# 2. SOURCE MATERIAL INGESTION (MOCK)
# ==========================================
def gather_source_materials():
    """Simulates pulling raw engineering footprints from APIs."""
    print("📥 Gathering source footprints (Jira, Slack, Git, Specs)...")
    payload = {
        "jira_tickets": ["JIRA-4021: Implement NVLink failover handling", "Status: Blocked by testing"],
        "slack_threads": ["Dave: 'Make sure to note that the timeout configuration defaults to 30s.'", "Elena: 'Agreed, and it requires sudo privileges.'"],
        "git_commits": ["feat: add nvlink-topology-check flag", "fix: resolve memory leak during warm reset"],
        "api_specs": ["POST /v1/topology/verify", "Headers: X-NV-Auth", "Returns: 200 OK or 503 Service Unavailable"]
    }
    return json.dumps(payload, indent=2)

# ==========================================
# 3. LLM GENERATION STAGE
# ==========================================
def generate_draft_with_llm(source_data):
    """Feeds engineering footprint data into LLM structured by our template rules."""
    print("🤖 Generating Markdown draft using template guidelines via LLM...")
    
    prompt = f"""
    You are an expert technical writer at an AI infrastructure company. 
    Using the raw source data below, write a comprehensive internal technical documentation draft in Markdown.
    
    CRITICAL STRUCTURE & RETRIEVAL REQURIEMENTS:
    1. Start with a '# Document Title' followed by a '## Summary' section.
    2. Include a metadata block containing: 'Ownership: [Specify Team]', 'Last Reviewed: 2026-06-12', and 'Keywords: [comma separated tags]'.
    3. Use clear task-based structural headings (e.g., '## How to Verify Topology').
    4. Include a '## Related Links' section at the bottom.
    
    STYLE COMPLIANCE:
    - Use active voice. Avoid acronyms without defining them first.
    - Highlight warnings using standard markdown blocks.

    RAW SOURCE DATA:
    {source_data}
    """
    
    response = ai_client.chat.completions.create(
        model="gpt-4o", # Can swap seamlessly to an internal Nvidia NeMo model endpoint
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )
    
    draft_content = response.choices[0].message.content
    
    # Save temporarily to run CLI tools against it
    with open("temp_draft.md", "w", encoding="utf-8") as f:
        f.write(draft_content)
        
    return "temp_draft.md"

# ==========================================
# 4. VALE LINTING STAGE
# ==========================================
def run_vale_linter(file_path):
    """Runs Vale CLI to parse style guide violations using programatic JSON tracking."""
    print("🔍 Running Vale automated style linting...")
    try:
        # Running vale outputting JSON so our script could optionally pass back fixes to the LLM
        result = subprocess.run(
            ["vale", "--output=JSON", file_path], 
            capture_output=True, 
            text=True, 
            check=False
        )
        
        violations = json.loads(result.stdout)
        if violations:
            print(f"⚠️ Vale found style issues in {file_path}:")
            print(json.dumps(violations, indent=2))
            print("💡 Script proceeding. Writer review required for full style reconciliation.")
        else:
            print("✅ Vale Linting Passed! No style guide discrepancies found.")
    except FileNotFoundError:
        print("⚠️ Warning: Vale CLI not installed or found in PATH. Skipping style lint check.")

# ==========================================
# 5. RETRIEVAL OPTIMIZATION VALIDATION
# ==========================================
def validate_retrieval_optimization(file_path):
    """Validates the markdown text strictly meets internal AI engine discoverability criteria."""
    print("📊 Validating AI retrieval and search optimization flags...")
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read().lower()
        
    validation_checks = {
        "Summary Section": "## summary" in content,
        "Ownership Field": "ownership:" in content,
        "Last Reviewed Date": "last reviewed:" in content,
        "Keywords/Tags": "keywords:" in content,
        "Related Links": "## related links" in content
    }
    
    all_passed = True
    for check, passed in validation_checks.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"  - Check [{check}]: {status}")
        if not passed:
            all_passed = False
            
    return all_passed

# ==========================================
# 6. CONFLUENCE STORAGE FORMAT EXPORT STAGE
# ==========================================
def convert_markdown_to_confluence_xhtml(file_path):
    """Converts native Markdown to Confluence Storage Format (XHTML)."""
    with open(file_path, "r", encoding="utf-8") as f:
        markdown_text = f.read()
        
    # In a production suite, we would use a robust converter library. 
    # For this script workflow, we construct the structure and apply structural wrappers.
    # We wrap our content into a distinct Confluence UI Info Macro block indicating automation state.
    macro_wrapper = (
        '<ac:structured-macro ac:name="info" ac:schema-version="1">'
        '<ac:rich-text-body><p><b>AUTOMATED DRAFT:</b> This technical document was compiled '
        'using doc_generator.py pipeline. Review and verify accuracy before publishing.</p>'
        '</ac:rich-text-body></ac:structured-macro>'
    )
    
    # Let's perform standard line conversion for paragraphs/headers to mock raw XHTML format
    xhtml_body = macro_wrapper
    for line in markdown_text.split("\n"):
        if line.startswith("# "):
            xhtml_body += f"<h1>{line[2:]}</h1>"
        elif line.startswith("## "):
            xhtml_body += f"<h2>{line[3:]}</h2>"
        elif line.strip():
            xhtml_body += f"<p>{line}</p>"
            
    return xhtml_body

def export_to_confluence(title, html_content):
    """Pushes payload securely to Confluence Instance as an unpolished draft."""
    print(f"🚀 Transporting draft to Confluence Space '{SPACE_KEY}'...")
    
    try:
        # Check if page already exists to prevent duplication
        page_exists = confluence.page_exists(SPACE_KEY, title)
        
        if page_exists:
            page_id = confluence.get_page_id(SPACE_KEY, title)
            print(f"🔄 Existing page found (ID: {page_id}). Updating page to a newer revision context...")
            confluence.update_page(
                page_id=page_id,
                title=title,
                body=html_content,
                parent_id=PARENT_PAGE_ID,
                type='page',
                representation='storage'
            )
        else:
            print("✨ Creating fresh documentation page entry...")
            confluence.create_page(
                space=SPACE_KEY,
                title=title,
                body=html_content,
                parent_id=PARENT_PAGE_ID,
                type='page',
                representation='storage'
            )
        print("🎉 Successfully exported! Document is ready for peer verification.")
    except Exception as e:
        print(f"❌ Critical error pushing to Confluence API: {e}")

# ==========================================
# MAIN EXECUTION ENGINE ENTRYPOINT
# ==========================================
if __name__ == "__main__":
    print("--- Starting Automated Docs-as-Code Pipeline ---")
    
    # 1. Ingest Raw footprints
    raw_materials = gather_source_materials()
    
    # 2. Process through LLM
    temp_file = generate_draft_with_llm(raw_materials)
    
    # 3. Automated Linter Guardrail
    run_vale_linter(temp_file)
    
    # 4. Search Optimization Gate
    retrieval_ready = validate_retrieval_optimization(temp_file)
    
    # 5. Conversion and Export to Target CMS
    confluence_xhtml = convert_markdown_to_confluence_xhtml(temp_file)
    doc_title = "[DRAFT] NVLink Failover Handling and Topology Verification Guide"
    
    export_to_confluence(doc_title, confluence_xhtml)
    
    # Cleanup local working directory lifecycle footprints
    if os.path.exists(temp_file):
        os.remove(temp_file)
        
    print("--- Pipeline Execution Finished Successfully ---")