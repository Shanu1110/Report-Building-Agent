# Report-Building-Agent
# DocDacity Intelligent Document Assistant

An interactive, LangGraph-powered document assistant for answering questions, summarizing records, and performing calculations over financial and healthcare-related documents. The project is intentionally self-contained: it ships with five sample documents and an in-memory retriever, so no database or vector store is required to run it.

The assistant combines LLM reasoning with typed responses, deterministic document tools, safe arithmetic evaluation, session memory, and transparent tool-use logging. It is designed as an educational foundation that can later be connected to a production document store.

## Contents

- [What it does](#what-it-does)
- [Features](#features)
- [Quick start](#quick-start)
- [Using the CLI](#using-the-cli)
- [Sample document library](#sample-document-library)
- [How it works](#how-it-works)
- [Tools](#tools)
- [Configuration](#configuration)
- [Project structure](#project-structure)
- [Development and validation](#development-and-validation)
- [Limitations and extension points](#limitations-and-extension-points)
- [Security notes](#security-notes)

## What it does

The application accepts natural-language requests such as:

- `What is the total due on invoice INV-002?`
- `Summarize all contracts`
- `Calculate the sum of all invoice totals`
- `Find documents with amounts over $50,000`
- `What is the status of claim CLM-001?`

For each request, the system classifies the intent, routes the request to a specialized agent, invokes document or calculation tools as needed, validates the result against a Pydantic schema, updates conversation memory, and prints the response with its detected intent, sources, and tools used.

## Features

- **Three task modes:** document Q&A, document summarization, and calculations.
- **PDF upload isolation:** load one text-based PDF and use it as the only active document source.
- **Structured intent routing:** `UserIntent` selects the appropriate LangGraph branch.
- **Typed model responses:** Q&A, summaries, calculations, and memory updates use Pydantic models.
- **Tool-assisted reasoning:** the agents can search documents, read full records, inspect collection statistics, and calculate arithmetic.
- **Amount-aware retrieval:** supports over, under, exact, approximate, and bounded-range queries.
- **Safe calculator:** parses arithmetic with Python's AST and allows only numeric values, parentheses, and basic arithmetic operators.
- **Conversation memory:** tracks message history, a generated summary, active document IDs, user ID, and session ID.
- **Session persistence:** stores session metadata and conversation history as JSON files.
- **Tool audit logs:** writes timestamped tool inputs and outputs to a session-specific JSON log.
- **OpenAI-compatible providers:** works with the configured course endpoint or another compatible API base URL.
- **Graph export:** exports the live LangGraph topology as Mermaid, with optional PNG rendering.
- **No external data service required:** sample data loads directly into memory at startup.

## Tech stack

| Area | Technology |
| --- | --- |
| Language | Python 3.10+ |
| Orchestration | LangGraph |
| LLM integration | LangChain, `langchain-openai`, OpenAI-compatible chat models |
| Validation | Pydantic v2 |
| Persistence | LangGraph `InMemorySaver` plus JSON files |
| Configuration | `python-dotenv` |
| PDF extraction | `pypdf` |
| Visualization | Mermaid graph export |
| Interface | Interactive terminal CLI with `print-color` |

## Quick start

### Prerequisites

- Python 3.10 or newer
- An API key for an OpenAI-compatible chat completion endpoint
- PowerShell on Windows, or a shell with equivalent virtual-environment commands

### Windows PowerShell

Run these commands from the repository's `starter` directory:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Open `.env` and set `OPENAI_API_KEY` before starting the assistant.

### macOS or Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

Then edit `.env` and set `OPENAI_API_KEY`.

### Start the assistant

```powershell
python main.py
```

The program asks for a user ID. Press Enter to use `demo_user`, then enter questions at the `Enter Message:` prompt.

## Using the CLI

Built-in commands:

| Command | Action |
| --- | --- |
| `/help` | Show commands and example prompts |
| `/docs` | List every document currently loaded in memory |
| `/upload <path>` | Replace the active documents with one PDF and start a fresh isolated session |
| `/reset` | Restore the built-in sample documents and start a fresh session |
| `/quit` | End the current session |

To upload a path containing spaces, quote it, for example:

```text
/upload "C:\Documents\annual report.pdf"
```

After a successful upload, searches, document reads, summaries, statistics, and calculations can access only the uploaded PDF. Uploading starts a new session thread so previous sample-document messages are not included in the new conversation context. Use `/reset` to return to the built-in sample library.

For normal messages, the CLI displays:

- The assistant's response
- The classified intent
- Source document IDs returned by the memory update step
- Tools invoked during the turn
- The current conversation summary

Example output metadata:

```text
INTENT: qa
SOURCES: INV-002
TOOLS USED: document_search, document_reader
```

The wording of the answer and the exact tool order are model-dependent. The available documents, tool implementations, schemas, and persisted records are deterministic for a given request and environment.

## Sample document library

`SimulatedRetriever` loads these records when `DocumentAssistant` starts:

| ID | Type | Title | Key data |
| --- | --- | --- | --- |
| `INV-001` | Invoice | Invoice #12345 | Acme Corporation; services; subtotal `$20,000`; tax `$2,000` |
| `CON-001` | Contract | Service Agreement | Healthcare Partners LLC; 12 months; contract value `$180,000` |
| `CLM-001` | Claim | Insurance Claim #78901 | Medical expense reimbursement; total claim amount `$2,450`; status Under Review |
| `INV-002` | Invoice | Invoice #12346 | TechStart Inc.; total due `$69,300`; Net 45 |
| `INV-003` | Invoice | Invoice #12347 | Global Corp; total due `$214,500`; Net 60 |

The content is defined in `starter/src/retrieval.py`. `SimulatedRetriever` supports adding additional `Document` objects at runtime through `add_document()`.

## How it works

### Request lifecycle

```text
User message
    |
    v
classify_intent
    |
    +--> qa_agent ------------------+
    +--> summarization_agent -------+--> update_memory --> END
    +--> calculation_agent ---------+
```

1. `main.py` loads environment variables, creates `DocumentAssistant`, starts a session, and reads CLI input.
2. `/upload <path>` uses `pypdf` to extract text page by page, replaces the retriever's document collection with one PDF document, and starts a fresh session thread.
3. `DocumentAssistant.process_message()` creates an `AgentState` and passes the session's `thread_id`, LLM, and tools through LangGraph configuration.
4. `classify_intent` uses structured output to classify the request as `qa`, `summarization`, `calculation`, or `unknown`. Unknown requests fall back to the Q&A branch.
5. The selected task agent uses a ReAct-style LangGraph agent with the relevant prompt and all four tools.
6. The task agent returns a typed response: `AnswerResponse`, `SummarizationResponse`, or `CalculationResponse`.
7. `update_memory` summarizes the turn and extracts relevant document IDs using `UpdateMemoryResponse`.
8. The assistant appends the turn to the session JSON file and returns response metadata to the CLI.

### State and persistence

`AgentState` contains the current input, LangChain messages, intent, next graph step, conversation summary, active document IDs, current response, tools used, session identity, conversation history, and accumulated actions.

There are two persistence mechanisms with different purposes:

- **LangGraph checkpointing:** `InMemorySaver` retains graph state for the current Python process. The session ID is used as the LangGraph `thread_id`.
- **JSON session storage:** `SESSION_STORAGE_PATH/<session_id>.json` stores the `SessionState`, including user ID, conversation history, document context, and timestamps. This supports loading session metadata again, but the in-memory graph checkpoint itself is not durable across process restarts.

Tool calls are written separately to `logs/session_<session_id>.json` with timestamps, inputs, outputs, and tool names.

### Structured schemas

- `UserIntent.intent_type` is restricted to `qa`, `summarization`, `calculation`, or `unknown`.
- `UserIntent.confidence` and `AnswerResponse.confidence` are constrained to the range `0.0` to `1.0`.
- `AnswerResponse` contains the question, answer, source IDs, confidence, and timestamp.
- `SummarizationResponse` contains the original length, summary, key points, document IDs, and timestamp.
- `CalculationResponse` contains the expression, numeric result, explanation, optional units, and timestamp.
- `UpdateMemoryResponse` contains the concise conversation summary and active document IDs.
- `SessionState` contains session identity, conversation history, document context, and timestamps.

## Tools

All tools are created in `starter/src/tools.py` and receive the shared retriever and `ToolLogger`.

| Tool | Purpose |
| --- | --- |
| `document_search` | Searches by keyword, document type, all documents, or amount criteria. Returns IDs, titles, types, amounts, relevance scores, and previews. |
| `document_reader` | Reads the complete content of a document by exact ID. |
| `document_statistics` | Reports document counts, type counts, amount totals, averages, minimums, and maximums. |
| `calculator` | Evaluates safe numeric expressions using `+`, `-`, `*`, `/`, `//`, `%`, `**`, unary signs, and parentheses. |

Amount searches can express:

- Minimum or maximum thresholds, such as over `$50,000` or under `$10,000`
- Inclusive ranges, such as between `$20,000` and `$80,000`
- Exact amounts
- Approximate amounts, using the retriever's default tolerance of plus or minus 10 percent

The amount-based retriever reads configured metadata fields such as `total`, `amount`, and `value`. Amounts that appear only in free-form document text are not automatically treated as indexed metadata for statistics and amount filtering.

## Configuration

The safe template is `starter/.env.example`. Copy it to `starter/.env` and keep the real file out of version control.

| Variable | Default | Description |
| --- | --- | --- |
| `OPENAI_API_KEY` | Required | Credential for the configured chat model endpoint. |
| `OPENAI_BASE_URL` | `https://openai.vocareum.com/v1` | OpenAI-compatible API base URL. Use `https://api.openai.com/v1` for the standard OpenAI API. |
| `MODEL_NAME` | `gpt-4o` | Chat model name accepted by the selected provider. |
| `TEMPERATURE` | `0.1` | Model sampling temperature parsed as a float. |
| `SESSION_STORAGE_PATH` | `./sessions` | Directory where session JSON files are written. |

Paths are resolved relative to the directory used to start the program. Running from `starter` is therefore recommended.

## Project structure

```text
project/
├── README.md
└── starter/
    ├── main.py                    # Interactive CLI entry point
    ├── requirements.txt           # Pinned Python dependencies
    ├── .env.example               # Safe environment template
    ├── src/
    │   ├── agent.py               # AgentState and LangGraph workflow
    │   ├── assistant.py           # LLM, tools, sessions, and invocation
    │   ├── prompts.py             # Intent, task, and memory prompts
    │   ├── retrieval.py           # Sample documents, PDF extraction, and retrieval
    │   ├── schemas.py             # Pydantic models and response contracts
    │   └── tools.py               # Search, reader, statistics, and calculator
    ├── scripts/
    │   └── export_graph.py        # Mermaid and optional PNG graph export
    ├── docs/
    │   └── langgraph_workflow.mmd # Exported workflow diagram
    ├── sessions/                  # Runtime JSON sessions; ignored by Git
    └── logs/                      # Runtime tool logs; ignored by Git
```

## Development and validation

Run these checks from `starter` after activating the virtual environment:

```powershell
python -m pip check
python -m compileall -q src main.py scripts
```

Export the current workflow graph without an API key:

```powershell
python scripts\export_graph.py
```

This refreshes `docs/langgraph_workflow.mmd`. To also attempt PNG rendering:

```powershell
python scripts\export_graph.py --png
```

The graph exporter constructs the workflow with `None` for the LLM and an empty tool list, so it does not contact an API. Full end-to-end requests require a valid key, a reachable endpoint, and a model that supports the structured output and tool-calling features used by the workflow.

## Limitations and extension points

This repository is a working educational prototype rather than a production document platform:

- Sample documents and uploaded PDF text are held in process memory.
- Retrieval is keyword- and metadata-based; there is no embeddings pipeline, vector database, OCR, or external document connector.
- PDF upload currently supports text-based PDFs with extractable text; scanned/image-only PDFs require OCR, which is not included.
- JSON session files are local and do not provide multi-user locking, encryption, or distributed storage.
- LangGraph checkpoints are lost when the process exits because `InMemorySaver` is used.
- There is no authentication, authorization, web UI, rate limiting, or API server.
- The LLM remains responsible for intent classification and response generation; tool outputs and typed schemas reduce ambiguity but do not replace domain review.
- The calculator restricts syntax, but callers should still validate financial results and units before using them operationally.

Natural next steps include replacing `SimulatedRetriever` with a database or vector store, adding document ingestion and chunking, selecting a durable LangGraph checkpointer, adding automated tests and CI, and exposing `DocumentAssistant` through an API or web interface.

## Security notes

- Never commit `.env`, API keys, session records, or logs containing sensitive data.
- Use a least-privilege API credential and a provider endpoint appropriate for the data being processed.
- Treat the bundled healthcare and financial content as synthetic sample data.
- Review and sanitize tool logs before sharing them because inputs and outputs may include document content.
- The calculator uses restricted AST validation and disables Python built-ins, but it should still be treated as an application feature that requires normal input validation and monitoring.
