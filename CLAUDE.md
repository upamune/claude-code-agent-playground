# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository is a playground for Claude Code agents experimentation and documentation collection. It contains:

- **Documentation archives**: Various Claude and Claude Code related documents fetched from official sources
- **Agent configurations**: Custom agent definitions in `.claude/agents/`
- **Utility scripts**: Python scripts for web content fetching and processing

## Architecture

### Key Directories

- `docs/`: Archived documentation from Claude AI and related projects
  - `claude/`: Claude-specific documentation including prompt engineering and guardrails
  - `claude_code/`: Claude Code specific documentation
  - `claude_code_sdk/`: SDK-related documentation
  - `python/`: Python-related documentation (e.g., PEP-723)
- `.claude/agents/`: Custom agent definitions for specialized tasks
- `scripts/`: Utility scripts for content fetching and processing

### Main Components

- **Document Fetcher**: `scripts/fetch_doc.py` - A PEP-723 compliant Python script that fetches web content and converts it to markdown with YAML frontmatter
- **Agent System**: Custom agents defined in `.claude/agents/` for specialized tasks like code review, research, and task management

## Development Tools

### Python Environment
- Uses `mise` for tool management (configured in `mise.toml`)
- Bunv version: 1.2.21 managed by mise

### Running Scripts
The main utility script uses PEP-723 inline script metadata:

```bash
# Run the document fetcher
./scripts/fetch_doc.py <URL>

# With debug mode
./scripts/fetch_doc.py <URL> --debug
```

The script automatically:
- Fetches content directly or via Jina Reader AI
- Extracts titles from HTML or markdown
- Adds YAML frontmatter with metadata
- Outputs markdown format

### Dependencies
Scripts use PEP-723 inline metadata format for dependency management. Dependencies are automatically resolved when running with compatible tools like `uv`.

## Custom Agents

The repository includes several specialized Claude Code agents:

- **code-reviewer**: Comprehensive code review with security, performance, and quality suggestions
- **research-assistant**: Information gathering and analysis for codebase analysis and technical research
- **sdk-showcase**: Comprehensive demonstration of Claude Code SDK features

Agents can be launched using the Task tool with the appropriate `subagent_type` parameter.

## Example Agents

The repository includes several runnable example agents in `agents/examples/`:

### Basic Examples
- **Hello Claude** (`agents/examples/hello_claude/main.py`): Simple greeting agent demonstrating basic SDK usage
- **Calculator** (`agents/examples/calculator/main.py`): Mathematical calculator with custom tools using `@tool` decorator
- **Streaming Input** (`agents/examples/streaming_input/main.py`): Demonstrates streaming message input to Claude

### Advanced Examples
- **Continuing Conversation** (`agents/examples/continuing_conversation/main.py`): Shows how to maintain conversation state across interactions
- **Using Interrupts** (`agents/examples/using_interrupts/main.py`): Demonstrates interrupt handling for user interventions
- **Advanced Permission Control** (`agents/examples/advanced_permission_control/main.py`): Fine-grained permission management example
- **Hooks** (`agents/examples/hooks/main.py`): Custom hook implementation for event-driven behavior

### Running Examples
All example agents use PEP-723 inline script metadata for dependency management:

```bash
# Run directly (if executable)
./agents/examples/hello_claude/main.py

# Or using uv
uv run --script agents/examples/hello_claude/main.py
```