
# ⚾ Baseball Fantasy Agent

**Live app:** [baseball-fantasy-agent.streamlit.app](https://baseball-fantasy-agent.streamlit.app/)

A fantasy baseball AI agent that answers natural-language questions about player stats, batting splits, and pitching performance using live MLB data. Ask it who to start, how a player hits on the road, or what a pitcher's season looks like — it pulls real stats from the MLB Stats API and returns data-backed recommendations.

Built with [smolagents](https://github.com/huggingface/smolagents) (Hugging Face's lightweight agent framework), Anthropic's Claude Haiku 4.5, and the [MLB Stats API](https://statsapi.mlb.com).

# ⚾ Baseball Fantasy Agent

**Live app:** [baseball-fantasy-agent.streamlit.app](https://baseball-fantasy-agent.streamlit.app/)

A fantasy baseball AI agent that answers natural-language questions about player stats, batting splits, and pitching performance using live MLB data. Ask it who to start, how a player hits on the road, or what a pitcher's season looks like — it pulls real stats from the MLB Stats API and returns data-backed recommendations.

Built with [smolagents](https://github.com/huggingface/smolagents) (Hugging Face's lightweight agent framework), Anthropic's Claude Haiku 4.5, and the [MLB Stats API](https://statsapi.mlb.com).

---

## What the Agent Can Do

### Supported Query Types

- **Season stats** — "How is Shohei Ohtani doing this season?"
- **Batting splits** — "How does Aaron Judge hit against left-handed pitchers?"
- **Home/away performance** — "How does Roman Anthony perform in away games?"
- **Pitching stats** — "What are Corbin Burnes' numbers this year?"
- **Start/sit recommendations** — "Should I start Mookie Betts tonight?"

### Scope and Boundaries

The agent answers questions about current-season MLB player performance for fantasy baseball decisions. It does not cover:

- Historical stats beyond the current season
- Team-level analysis or standings
- Trade valuations or dynasty league strategy
- Injury news or roster moves
- Non-MLB leagues

If the agent cannot answer a question with its available tools, it says so directly rather than guessing.

---

## How It Works

### Architecture

The agent runs a reasoning loop: receive a question, select a tool, call it, interpret the result, and deliver an answer. The framework (smolagents) manages this loop. The model (Claude Haiku 4.5) decides which tool to call and how to interpret the response.

### Tools

The agent has three tools. Each is a Python function decorated with `@tool`, which exposes the function signature and docstring to the model as a callable schema.

| Tool | Purpose | Key Parameters |
|---|---|---|
| `get_batter_stats` | Current season batting stats | `player_name` |
| `get_player_splits` | Batting performance by situation | `player_name`, `split_code` (h, a, vl, vr, d, n) |
| `get_pitcher_stats` | Current season pitching stats | `player_name` |

All three tools query the MLB Stats API, validate the response, and return structured dictionaries. If a player is not found or data is unavailable, the tool returns a descriptive error string instead.

### Decision Logic

The model selects tools based on the question:

- Mentions of "season," "this year," or general performance → `get_batter_stats` or `get_pitcher_stats`
- Mentions of "home," "away," "road," "left-handed," "right-handed," "day," "night" → `get_player_splits`
- Position players default to batting tools; pitchers route to `get_pitcher_stats`

This routing is governed by the system prompt and tool docstrings, not hard-coded logic. The model interprets the question and matches it to the tool whose docstring best fits.

---

## Agent Behavior and Limitations

### Sample Size Thresholds

The agent flags small sample sizes in its responses:

- Under 50 at-bats for batters — conclusions are unreliable
- Under 50 innings pitched for starters — same
- Under 15 innings pitched for relievers — same

### Response Characteristics

- Leads with a direct answer before supporting stats
- Cites specific numbers from the tool response (never fabricates)
- Includes fantasy-relevant context (OPS emphasis over batting average, platoon implications)
- Typical response time: 3–5 seconds
- Typical cost per query: < $0.01 (Claude Haiku 4.5)

### Known Limitations

- **Single-season scope.** No year-over-year trends or career stats.
- **No schedule awareness.** The agent does not know who is pitching tonight or which teams are playing. It cannot factor upcoming matchups into recommendations unless the user provides that context.
- **No injury data.** The agent does not know if a player is on the injured list.
- **Split codes are manual.** The user must phrase questions in a way the model maps to a split code. Unusual splits (e.g., performance on turf vs. grass) are not supported.

---

## Development Log

### Architecture Decisions

**Why smolagents:** Model-agnostic via LiteLLM. The same agent code ran against local Ollama during development and Anthropic's hosted API in production — the only change was the `model_id` string. Tool definitions use a decorator pattern (`@tool` + docstring), which keeps tool schemas colocated with the implementation.

**Why ToolCallingAgent over CodeAgent:** CodeAgent executes model-generated Python in a sandbox, which gives the model freedom to compute intermediate values. In practice, this freedom allowed the model to fabricate statistics (inventing formulas like "weighted batting average") and shadow the `final_answer` tool by assigning to the variable name. ToolCallingAgent constrains the model to structured tool calls and natural-language responses, eliminating both failure modes.

**Why Claude Haiku 4.5:** Tested four models during development. Haiku terminates reliably in two steps, passes correct arguments, interprets results accurately, and costs fractions of a cent per query. Larger or more expensive models offered no measurable improvement for this use case.

### Iteration History

| Version | Agent Type | Model | Result |
|---|---|---|---|
| v1a | CodeAgent | Llama 3.2 3B (local) | Fabricated statistics; delivered wrong recommendation despite correct tool data |
| v1b | ToolCallingAgent | Llama 3.2 3B (local) | Correct answer but 9 redundant tool calls before termination |
| v1c | ToolCallingAgent | Llama 3.1 8B (local) | Tool called with empty arguments; model/framework format mismatch |
| v1d | ToolCallingAgent | Qwen 2.5 7B (local) | Correct in 2 steps; validated the ToolCallingAgent architecture |
| **v1 (shipped)** | **ToolCallingAgent** | **Claude Haiku 4.5 (API)** | **Correct in 2 steps, 4.4 seconds, detailed and actionable answer** |

### Key Findings

**Prompt-level instructions are weaker than structural constraints.** Adding "never fabricate statistics" to the system prompt did not prevent CodeAgent from inventing formulas. Switching to ToolCallingAgent — which removes code execution entirely — eliminated the failure mode structurally. The effective fix was removing the capability, not adding an instruction.

**Bigger model ≠ better agent.** Llama 3.1 8B (larger) performed worse than Llama 3.2 3B (smaller) because the 8B model's tool-calling format was incompatible with the smolagents/LiteLLM/Ollama stack. Model selection for agents depends on framework compatibility, not just parameter count.

**Tool docstrings are part of the system.** The model selects tools and passes arguments based on docstrings. A vague docstring produces wrong tool calls. Docstring quality directly affects agent accuracy — they function as prompt engineering, not just developer documentation.

---