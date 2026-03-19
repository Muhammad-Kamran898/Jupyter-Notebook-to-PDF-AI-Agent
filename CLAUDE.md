# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Jupyter notebook to PDF conversion agent (`nb2pdf_agent`) that transforms `.ipynb` files into professional PDF reports. The agent uses local Ollama AI to provide code explanations within the generated PDF.

## Commands

```bash
# Run the PDF conversion agent (output goes to pdf_reports/)
python nb2pdf_agent.py <notebook.ipynb>

# With custom output name
python nb2pdf_agent.py <notebook.ipynb> <output_name.pdf>

# Install dependencies
uv add nbformat markdown pygments weasyprint requests ipykernel
```

## Architecture

The project has two entry points:
- `main.py` - Stub (unused for conversion)
- `nb2pdf_agent.py` - Core agent

Processing pipeline:
1. Parse notebook JSON (`nbformat`)
2. Extract markdown headers (H1-H3) for TOC
3. For each code cell: query Ollama, syntax highlight, process outputs
4. Build styled HTML
5. Convert to PDF (`weasyprint`) → save to `pdf_reports/`

## Key Dependencies

| Package | Purpose |
|---------|---------|
| nbformat | Jupyter notebook JSON parsing |
| markdown | Markdown to HTML conversion |
| pygments | Python syntax highlighting |
| weasyprint | HTML to PDF rendering |
| requests | HTTP client for Ollama API |

- **Python**: 3.11+
- **Ollama**: Running on localhost:11434 (optional)

## Core Functions

- `get_ollama_clarification()` - Queries Ollama for AI explanations
- `clean_ansi()` - Removes terminal escape codes
- `build_agent_report()` - Main conversion logic

## Notes

- Default Ollama model: `llama3.2`
- PDF output: `pdf_reports/` folder (auto-created)
- If Ollama unavailable, PDF generates with fallback message
- PDFs include dynamic page numbers and auto-generated TOC
- WeasyPrint requires GTK3 on Windows