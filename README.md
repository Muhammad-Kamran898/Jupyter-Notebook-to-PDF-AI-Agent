# Jupyter to PDF Agent (`nb2pdf_agent`)

An AI-powered document parsing agent that converts raw Jupyter Notebooks (`.ipynb`) into beautifully formatted, professional PDF and TXT reports.

Instead of dumping raw notebook visuals, this agent programmatically parses the underlying JSON, renders markdown, applies syntax highlighting to code, formats outputs (including Pandas DataFrames and plots), and compiles a polished PDF featuring a Table of Contents and dynamic page numbers.

## Features

- **AI-Powered Explanations**: Queries local Ollama instance with auto-model selection
- **Smart Model Selection**: Automatically selects best model based on notebook complexity (Deep Learning, ML, or Basic Analysis)
- **Parallel Processing**: Batches code cells and processes them concurrently (4 workers)
- **Syntax Highlighting**: Beautiful Python code highlighting using Pygments
- **Table of Contents**: Auto-generated TOC from markdown headers (H1-H3)
- **Professional PDF Output**: Clean, formatted PDFs with page numbers
- **Dual Output**: Generates both PDF and TXT reports simultaneously
- **Multiple Output Formats**: Handles text, HTML, images (PNG), and error messages
- **Error Handling**: Includes AI-powered error analysis with retry logic
- **Progress Tracking**: Real-time progress bar using tqdm

## Requirements

- Python 3.11 or higher
- [Ollama](https://ollama.com/) installed and running locally (for AI features - optional)

## Installation

### 1. Install Python Dependencies

Using uv (recommended):
```bash
uv add nbformat markdown pygments weasyprint requests tqdm argparse
```

Or using pip:
```bash
pip install nbformat markdown pygments weasyprint requests tqdm argparse
```

### 2. Install Ollama (Optional - for AI features)

Ollama is required only if you want the AI code explanations feature.

**Windows:**
- Download and install from [ollama.com](https://ollama.com/download/windows)

**macOS:**
```bash
brew install ollama
```

**Linux:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

After installation, start Ollama:
```bash
ollama serve
```

Then pull the model (default: llama3.2):
```bash
ollama pull llama3.2
```

## Usage

### Basic Usage

Convert a single notebook to PDF and TXT:
```bash
python nb2pdf_agent.py input_notebook.ipynb
```

This will generate:
- `pdf_reports/input_notebook_report.pdf`
- `txt_reports/input_notebook_flow.txt`

### Custom Output Paths

Specify custom output filenames:
```bash
python nb2pdf_agent.py notebook.ipynb --pdf my_report.pdf --txt notes.txt
```

### Select AI Model

Choose a specific Ollama model or use auto-selection:
```bash
# Auto-select based on notebook complexity (default)
python nb2pdf_agent.py notebook.ipynb --model auto

# Use specific model
python nb2pdf_agent.py notebook.ipynb --model llama3.2
python nb2pdf_agent.py notebook.ipynb --model phi4
```

### Command Line Options

| Argument | Description |
|----------|-------------|
| `notebook` | Path to the input .ipynb file (required) |
| `--pdf` | Custom PDF output path |
| `--txt` | Custom TXT output path |
| `--model` | Ollama model to use (default: auto) |

## How It Works

```
┌─────────────────┐     ┌──────────────────┐     ┌──────────────┐
│  Jupyter .ipynb │ ──► │ nb2pdf_agent.py  │ ──► │ pdf_reports/ │
│     (Input)     │     │   (Processing)   │     │  txt_reports │
└─────────────────┘     └──────────────────┘     └──────────────┘

Processing Steps:
1. Parse notebook JSON using nbformat
2. Extract markdown headers for Table of Contents
3. Analyze notebook complexity → auto-select best Ollama model
4. Batch code cells (size=4) for parallel processing
5. For each batch:
   - Query Ollama for AI explanations (with retry logic)
   - Apply syntax highlighting with Pygments
   - Process cell outputs (text, images, errors)
6. Build styled HTML document
7. Convert to PDF using WeasyPrint
8. Export TXT report
```

### Auto Model Selection Logic

The agent analyzes your notebook content to select the best model:

| Detected Libraries | Complexity | Preferred Models |
|-------------------|------------|------------------|
| torch, tensorflow, keras, transformers | High | llama3:8b, phi4, gemma:7b |
| sklearn, xgboost, lightgbm | Medium | mistral, llama3:8b, phi3 |
| Basic Python/Data Analysis | Low | llama3.2, qwen2.5:0.5b |

## Output Features

- **Table of Contents**: Auto-generated from markdown headers (H1-H3)
- **Page Numbers**: Dynamic page numbering at bottom-right
- **Code Highlighting**: Syntax-highlighted Python code
- **AI Explanations**: Purple-highlighted boxes showing model used and explanation
- **Output Formatting**: Blue-bordered output sections
- **Error Display**: Red-highlighted error messages with fix suggestions
- **Image Support**: Inline PNG images
- **Table Support**: Properly formatted Pandas DataFrames and markdown tables

## Project Structure

```
.
├── main.py                    # Simple entry point
├── nb2pdf_agent.py            # Main conversion agent
├── pyproject.toml             # Project configuration
├── README.md                  # This file
├── CLAUDE.md                  # AI assistant guidance
├── notebooks/                 # Input notebooks directory
│   └── (your .ipynb files)
├── pdf_reports/               # Generated PDF outputs
│   └── (generated PDFs)
└── txt_reports/               # Generated TXT outputs
    └── (generated TXT files)
```

## Dependencies

| Package | Purpose |
|---------|---------|
| nbformat | Read/parse Jupyter notebook JSON |
| markdown | Convert Markdown to HTML |
| pygments | Syntax highlighting |
| weasyprint | HTML to PDF conversion |
| requests | HTTP client for Ollama API |
| tqdm | Progress bar for batch processing |
| argparse | Command-line argument parsing |

## Configuration

You can modify batch processing settings in `nb2pdf_agent.py`:

```python
BATCH_SIZE = 4   # Number of cells per batch
MAX_WORKERS = 4  # Parallel workers for processing
```

## Troubleshooting

### Ollama Connection Error

If you see: `*AI Clarification unavailable: Could not connect to Ollama...*`

**Solution:**
1. Make sure Ollama is installed: `ollama --version`
2. Start Ollama service: `ollama serve`
3. Pull the model: `ollama pull llama3.2`

The PDF will still be generated, just without AI explanations.

### WeasyPrint Issues (Windows)

If you encounter WeasyPrint errors on Windows, you may need to install GTK3:
- Download GTK3 from: https://github.com/SteaI/gtk3-installer/releases

### PDF Rendering Issues

If the PDF doesn't render correctly:
1. Check that all dependencies are installed correctly
2. Ensure the input notebook is a valid .ipynb file
3. Try updating WeasyPrint: `pip install --upgrade weasyprint`

## License

MIT License