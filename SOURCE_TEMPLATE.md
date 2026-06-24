# Source Material Template
#
# Copy this file, rename it for your topic, and fill in the sections.
# Delete any sections that don't apply. The pipeline reads everything
# in sources/ and feeds it to the LLM as raw context.
#
# The more specific you are here, the better the generated doc.

## Topic
# What is this document about? One sentence.


## Audience
# Who reads this? (e.g., backend engineers, DevOps, new hires, external developers)


## Jira / Tickets
# Paste ticket IDs, summaries, acceptance criteria, status.
# Example:
# PROJ-101: Implement retry logic for upstream timeout
# Status: In Review
# AC: Retry 3x with exponential backoff, log each attempt


## Slack / Conversations
# Paste relevant thread snippets. Include who said what.
# Example:
# Dave: "Default timeout is 30s, needs sudo to change."
# Elena: "Document the config file path too."


## Git History
# Paste relevant commit messages or PR descriptions.
# Example:
# feat: add health-check endpoint
# fix: resolve connection pool leak on restart
# PR #42: Adds /v1/health/verify with bearer auth


## API Specs
# Paste endpoint details, request/response formats, auth requirements.
# Example:
# POST /v1/health/verify
# Headers: Authorization: Bearer <token>
# Response: 200 OK | 503 Service Unavailable
# Body: { "status": "healthy", "uptime_seconds": 84200 }


## Architecture / Design Decisions
# Why was it built this way? What alternatives were considered?
# Example:
# Chose polling over webhooks because the upstream API doesn't support push.
# Evaluated Redis and Memcached for caching; went with Redis for pub/sub support.


## Known Limitations
# What doesn't work? What's out of scope?
# Example:
# No support for batch requests yet (planned for Q3).
# Rate limited to 100 req/min per token.


## Related Docs / Links
# Existing docs, design specs, or external references.
# Example:
# Design spec: https://docs.google.com/doc/d/xxxxx
# Upstream API docs: https://api.example.com/docs
