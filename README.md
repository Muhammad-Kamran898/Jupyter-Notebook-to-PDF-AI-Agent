# Jupyter to PDF Agent (`nb2pdf_agent`)

An AI-powered document parsing agent that converts raw Jupyter Notebooks (`.ipynb`) into beautifully formatted, professional PDF reports.

Instead of dumping raw notebook visuals, this agent programmatically parses the underlying JSON, renders markdown, applies syntax highlighting to code, formats outputs (including Pandas DataFrames and plots), and compiles a polished PDF featuring a Table of Contents and dynamic page numbers.

## Requirements

Ensure you have Python 3.8+ installed.

1. **Install Python Dependencies:**

   ```bash
   pip install nbformat markdown pygments weasyprint
