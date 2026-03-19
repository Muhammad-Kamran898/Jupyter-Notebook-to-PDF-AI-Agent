# 📄 Jupyter Notebook to PDF Agent (`nb2pdf_agent`)

![nb2pdf Demo](https://via.placeholder.com/800x400.png?text=GIF+of+Terminal+Running+then+PDF+Opening)  
*(Tip: Record a quick 5-10 second GIF of your script running and the PDF opening, upload it to your repo, and replace this link!)*

![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Local AI](https://img.shields.io/badge/AI-Ollama-purple.svg)
![Maintained](https://img.shields.io/badge/Maintained%3F-yes-green.svg)

---

An **AI-powered document parsing agent** that converts raw Jupyter Notebooks (`.ipynb`) into **beautifully formatted, professional PDF and TXT reports**.

Instead of dumping raw notebook visuals, this agent:

- Programmatically parses the notebook JSON
- Renders Markdown
- Applies syntax highlighting to code
- Formats outputs (including Pandas DataFrames, plots, and images)
- Compiles a polished PDF featuring a **Table of Contents** and **dynamic page numbers**

---

## 💡 Why use `nb2pdf_agent` over `jupyter nbconvert`?

Standard Jupyter-to-PDF converters often:

- Break layouts  
- Cut off code  
- Require massive LaTeX installations  

**nb2pdf_agent** bypasses LaTeX entirely, using **HTML/CSS for perfect formatting** and a **local AI agent** to automatically read your code and generate professional explanations for **every cell**.  

It transforms a messy scratchpad into a **boardroom-ready document in seconds**.

---

## ✨ Features

- **AI-Powered Explanations**: Queries your local Ollama instance to explain each code cell.  
- **Smart Model Selection**: Automatically picks the best model for your notebook complexity.  
- **Fast Fallback**: Defaults to a lightweight model if heavy models aren’t available.  
- **Parallel Processing**: Batches code cells and processes them concurrently.  
- **Syntax Highlighting**: Beautiful Python code highlighting using Pygments.  
- **Table of Contents**: Auto-generated from notebook Markdown headers.  
- **Professional PDF Output**: Clean, formatted PDFs with dynamic page numbers.  
- **Error Handling**: AI-powered error analysis explains *why code breaks and how to fix it*.  

---

## ⚙️ Requirements

- **Python 3.11+**  
- [**Ollama**](https://ollama.com/) installed and running locally (for AI features)

---

## 🚀 Installation

### 1️⃣ Python Dependencies

Using **uv** (recommended):

```bash
uv add nbformat markdown pygments weasyprint requests tqdm argparse

Or using pip:

pip install nbformat markdown pygments weasyprint requests tqdm argparse
2️⃣ Install Ollama

Windows: Download from ollama.com

macOS: brew install ollama

Linux:

curl -fsSL https://ollama.com/install.sh | sh

After installation, start Ollama and pull your preferred model:

ollama serve
ollama pull llama3.2
💻 Usage

Convert a single notebook to PDF + TXT automatically:

python nb2pdf_agent.py input_notebook.ipynb
Advanced Commands
# Custom output filenames
python nb2pdf_agent.py notebook.ipynb --pdf my_report.pdf --txt notes.txt

# Force a specific model instead of auto-detecting
python nb2pdf_agent.py notebook.ipynb --model phi4
🧠 Auto Model Selection Logic

The agent analyzes your notebook to pick the best model:

Detected Libraries	Complexity	Preferred Models
torch, tensorflow, keras, transformers	High	llama3:8b, phi4, gemma:7b
sklearn, xgboost, lightgbm	Medium	mistral, llama3:8b, phi3
Basic Python / Data Analysis	Low	llama3.2, qwen2.5:0.5b

If no preferred model is found, it falls back safely to the fastest lightweight model installed.

🛠️ Troubleshooting

Ollama Connection Error: If you see *AI Clarification unavailable*, ensure Ollama is running (ollama serve).

WeasyPrint Issues (Windows): If PDF rendering fails, install GTK3.

☕ Support the Project

If this tool saved you hours of formatting documentation or helped with assignments/presentations:

⭐ Star this repository

☕ Buy me a coffee on Ko-fi

📄 License

MIT License
