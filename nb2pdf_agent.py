import sys
import os
import re
import requests
import argparse
import nbformat
import markdown
from pygments import highlight
from pygments.lexers import PythonLexer
from pygments.formatters import HtmlFormatter
from weasyprint import HTML
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

# ---------------------------
# CONFIG
BATCH_SIZE = 4
MAX_WORKERS = 4
# ---------------------------


def get_installed_ollama_models():
    """Fetches the list of models currently downloaded in your local Ollama instance."""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        response.raise_for_status()
        models = [model["name"] for model in response.json().get("models", [])]
        return models
    except requests.exceptions.RequestException:
        print(
            "[-] Warning: Could not connect to Ollama to fetch models. Is Ollama running?"
        )
        return []


def auto_select_model(nb, installed_models):
    """Analyzes notebook complexity and automatically selects the best installed model."""
    if not installed_models:
        return "llama3.2"  # Ultimate fallback if we can't fetch the list

    print("[*] Analyzing notebook complexity for auto-model selection...")

    full_code = ""
    for cell in nb.cells:
        if cell.cell_type == "code":
            full_code += cell.source.lower() + "\n"

    # Define complexity tiers and preferred models for each
    heavy_models = ["llama3:8b", "phi4", "gemma:7b", "mistral"]
    mid_models = ["mistral", "llama3:8b", "phi3"]
    light_models = ["llama3.2", "qwen2.5:0.5b", "gemma:2b", "mistral"]

    # Heuristic 1: Deep Learning / Advanced Math (High Complexity)
    if any(
        lib in full_code
        for lib in ["import torch", "import tensorflow", "import keras", "transformers"]
    ):
        print("    -> Detected High Complexity (Deep Learning/AI)")
        preferred_list = heavy_models
    # Heuristic 2: Standard Machine Learning (Medium Complexity)
    elif any(
        lib in full_code
        for lib in ["import sklearn", "from sklearn", "xgboost", "lightgbm"]
    ):
        print("    -> Detected Medium Complexity (Standard Machine Learning)")
        preferred_list = mid_models
    # Heuristic 3: Basic Data Analysis / Python (Low Complexity)
    else:
        print("    -> Detected Low Complexity (Basic Data Analysis)")
        preferred_list = light_models

    # Find the first preferred model that is actually installed
    for pref in preferred_list:
        for installed in installed_models:
            if installed.startswith(pref) or pref.startswith(installed.split(":")[0]):
                return installed

    # --- UPGRADED FALLBACK LOGIC ---
    print(
        "    -> Preferred models not found. Searching for the fastest available fallback..."
    )

    # List of known fast/lightweight models
    lightweight_safeties = ["qwen", "llama3.2", "gemma:2b", "mistral", "phi3"]

    # Try to find a lightweight model to fail gracefully and fast
    for safe_model in lightweight_safeties:
        for installed in installed_models:
            if safe_model in installed:
                print(f"    -> Safe fallback triggered. Using fast model: {installed}")
                return installed

    # Ultimate emergency fallback (if you literally only have one random model installed)
    fallback = installed_models[0]
    print(f"    -> No recognized safe fallbacks. Blindly falling back to: {fallback}")
    return fallback


def get_ollama_clarification(prompt, model_name):
    """Queries the local Ollama instance."""
    url = "http://localhost:11434/api/generate"
    payload = {"model": model_name, "prompt": prompt, "stream": False}

    try:
        response = requests.post(url, json=payload, timeout=120)
        response.raise_for_status()
        return response.json().get("response", "")
    except requests.exceptions.ConnectionError:
        return f"*AI Clarification unavailable: Could not connect to Ollama (Model: {model_name}).*"
    except Exception as e:
        return f"*AI Clarification error: {str(e)}*"


def clean_ansi(text):
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi_escape.sub("", text)


def build_agent_report(
    notebook_path, output_pdf_path, output_txt_path, user_model_choice
):
    print(f"[*] Agent reading notebook: {notebook_path}")

    with open(notebook_path, "r", encoding="utf-8") as f:
        nb = nbformat.read(f, as_version=4)

    # --- AUTO MODEL SELECTION LOGIC ---
    if user_model_choice.lower() == "auto":
        installed_models = get_installed_ollama_models()
        model_name = auto_select_model(nb, installed_models)
    else:
        model_name = user_model_choice

    print(f"[*] Locked in AI Model for this run: {model_name}")

    toc_items = []
    master_html_cells = {}
    master_txt_cells = {}
    code_cells_info = []

    pygments_formatter = HtmlFormatter(style="default", cssclass="syntax-highlight")
    css_syntax = pygments_formatter.get_style_defs()

    print("[*] Preparing cells and extracting Markdown...")

    # 1. Collect cells
    for i, cell in enumerate(nb.cells):
        if cell.cell_type == "markdown":
            for line in cell.source.split("\n"):
                if line.startswith("#"):
                    level = len(line) - len(line.lstrip("#"))
                    title = line.lstrip("#").strip()
                    anchor = title.lower().replace(" ", "-").replace(".", "")
                    if 1 <= level <= 3:
                        toc_items.append(
                            {"level": level, "title": title, "anchor": anchor}
                        )

            md_html = markdown.markdown(
                cell.source, extensions=["tables", "fenced_code", "toc"]
            )
            master_html_cells[i] = f'<div class="markdown-block">{md_html}</div>'

            if output_txt_path:
                txt_content = (
                    "\n".join(cell.source.splitlines()) + "\n" + "-" * 80 + "\n"
                )
                master_txt_cells[i] = txt_content

        elif cell.cell_type == "code":
            if cell.source.strip():
                code_cells_info.append(
                    {"index": i, "code": cell.source, "outputs": cell.outputs}
                )
            else:
                master_html_cells[i] = ""
                master_txt_cells[i] = ""

    # 2. Create batches
    batches = [
        code_cells_info[i : i + BATCH_SIZE]
        for i in range(0, len(code_cells_info), BATCH_SIZE)
    ]
    print(
        f"[*] Total active code cells: {len(code_cells_info)}, Batches: {len(batches)}"
    )

    def process_batch(batch_num, batch):
        batch_prompt = (
            "You are an expert data scientist. I will give you multiple Python code cells. "
            "For EACH cell, explain what it does in 2-3 sentences. If there is an Error, explain how to fix it.\n"
            "CRITICAL INSTRUCTION: You MUST start your explanation for each cell with the exact tag [CELL_ID_X] where X is the cell number. "
            "Do not use markdown blocks around the whole response.\n\n"
        )

        for info in batch:
            idx = info["index"]
            code_text = info["code"]
            error_text = ""
            if info["outputs"]:
                for output in info["outputs"]:
                    if output.output_type == "error":
                        error_text = clean_ansi("\n".join(output.traceback))

            batch_prompt += f"--- START CODE FOR CELL {idx} ---\n{code_text}\n"
            if error_text:
                batch_prompt += f"Error output:\n{error_text}\n"
            batch_prompt += f"--- END CODE FOR CELL {idx} ---\n\n"

        response_text = get_ollama_clarification(batch_prompt, model_name=model_name)
        processed_cells = []

        for info in batch:
            idx = info["index"]
            explanation = ""

            pattern = rf"\[CELL_ID_{idx}\](.*?)(?=\[CELL_ID_|$)"
            match = re.search(pattern, response_text, re.DOTALL | re.IGNORECASE)

            if match and match.group(1).strip():
                explanation = match.group(1).strip()
                if explanation.startswith("```"):
                    explanation = explanation.strip("`\n").strip()

            # AUTO-RETRY FALLBACK
            if not explanation:
                cell_error = ""
                if info["outputs"]:
                    for output in info["outputs"]:
                        if output.output_type == "error":
                            cell_error = clean_ansi("\n".join(output.traceback))

                fallback_prompt = (
                    "You are an expert data scientist. Explain what this specific Python code does conceptually in 2-3 sentences. "
                    "If there is an Error, explain why and how to fix it. Just provide the explanation text directly.\n\n"
                    f"Code:\n{info['code']}\n"
                )
                if cell_error:
                    fallback_prompt += f"Error output:\n{cell_error}\n"

                explanation = get_ollama_clarification(
                    fallback_prompt, model_name=model_name
                ).strip()

                if not explanation:
                    explanation = f"*AI Explanation failed completely after retry with model {model_name}.*"

            # HTML Build
            ai_html = markdown.markdown(
                f"**🤖 AI Analysis ({model_name}):**\n{explanation}"
            )
            code_html = highlight(info["code"], PythonLexer(), pygments_formatter)
            cell_html = f'<div class="ai-clarification">{ai_html}</div><div class="code-block">{code_html}</div>'

            # TXT Build
            cell_txt = f"# Cell {idx + 1}\n{info['code']}\n\nAI Explanation ({model_name}):\n{explanation}\n"

            outputs = info["outputs"]
            if outputs:
                cell_html += '<div class="output-block">'
                for output in outputs:
                    if output.output_type == "stream":
                        clean_out = clean_ansi(output.text)
                        cell_html += f'<pre class="output-stream">{clean_out}</pre>'
                        cell_txt += f"\nOutput:\n{clean_out}"
                    elif output.output_type in ["execute_result", "display_data"]:
                        data = output.data
                        if "text/html" in data:
                            cell_html += (
                                f'<div class="output-html">{data["text/html"]}</div>'
                            )
                        elif "image/png" in data:
                            cell_html += f'<img class="output-image" src="data:image/png;base64,{data["image/png"]}" alt="PNG Output"/>'

                        if "text/plain" in data:
                            if "text/html" not in data and "image/png" not in data:
                                cell_html += f'<pre class="output-plain">{data["text/plain"]}</pre>'
                            cell_txt += f"\nOutput:\n{data['text/plain']}"
                    elif output.output_type == "error":
                        traceback_text = clean_ansi("\n".join(output.traceback))
                        cell_html += f'<pre class="output-error">{traceback_text}</pre>'
                        cell_txt += f"\nError:\n{traceback_text}"
                cell_html += "</div>"

            cell_txt += "\n" + "-" * 80 + "\n"
            processed_cells.append((idx, cell_html, cell_txt))

        return processed_cells

    # 3. Process batches in parallel
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(process_batch, i + 1, batch): i
            for i, batch in enumerate(batches)
        }
        for future in tqdm(
            as_completed(futures), total=len(futures), desc="Processing AI Batches"
        ):
            for idx, html_content, txt_content in future.result():
                master_html_cells[idx] = html_content
                master_txt_cells[idx] = txt_content

    # 4. Reassemble exactly in original order
    final_html_cells = [
        master_html_cells[i] for i in range(len(nb.cells)) if i in master_html_cells
    ]
    final_txt_lines = [
        master_txt_cells[i] for i in range(len(nb.cells)) if i in master_txt_cells
    ]

    # 5. Assemble TOC
    toc_html = (
        "<div class='toc-container'><h2>Table of Contents</h2><ul class='toc-list'>"
    )
    if toc_items:
        for item in toc_items:
            indent_class = f"toc-level-{item['level']}"
            toc_html += f"<li class='{indent_class}'><a href='#{item['anchor']}'>{item['title']}</a></li>"
        toc_html += "</ul></div><div class='page-break'></div>"
    else:
        toc_html = "<div class='toc-container'><h2>Report Content</h2><p style='color: #666;'>No structural headers found.</p></div><div class='page-break'></div>"

    # 6. Generate PDF
    master_html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <style>
            {css_syntax}
            @page {{ size: A4; margin: 2cm; @bottom-right {{ content: "Page " counter(page) " of " counter(pages); color: #666; font-family: Arial; font-size: 9pt; }} }}
            body {{ font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; line-height: 1.6; color: #333; font-size: 11pt; }}
            .page-break {{ page-break-after: always; }}
            .ai-clarification {{ background-color: #f3e8fa; padding: 12px; border-radius: 6px; margin-bottom: 8px; border-left: 4px solid #8e44ad; font-size: 10pt; }}
            .code-block {{ background-color: #f8f9fa; border: 1px solid #e9ecef; border-radius: 4px; padding: 10px; margin-bottom: 5px; font-family: 'Courier New', monospace; font-size: 9pt; overflow-x: auto; }}
            .output-block {{ background-color: #ffffff; border-left: 4px solid #007bff; padding: 10px; margin-bottom: 20px; font-size: 9pt; }}
            .output-stream, .output-plain, .output-error {{ white-space: pre-wrap; font-family: 'Courier New', monospace; margin: 0; }}
            .output-error {{ color: #dc3545; }}
            .output-image {{ max-width: 100%; height: auto; margin-top: 10px; }}
            .toc-container {{ margin-bottom: 30px; }}
            .toc-list {{ list-style-type: none; padding-left: 0; }}
            .toc-level-1 {{ font-weight: bold; margin-top: 10px; }}
            .toc-level-2 {{ margin-left: 20px; }}
        </style>
    </head>
    <body>
        {toc_html}
        {"".join(final_html_cells)}
    </body>
    </html>
    """

    print("\n[*] Rendering Professional PDF...")
    HTML(string=master_html).write_pdf(output_pdf_path)
    print(f"[+] Success! PDF generated at: {output_pdf_path}")

    # 7. Export TXT
    if output_txt_path:
        with open(output_txt_path, "w", encoding="utf-8") as ftxt:
            ftxt.write("".join(final_txt_lines))
        print(f"[+] Text flow exported at: {output_txt_path}")


# -------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert Jupyter Notebooks to AI-explained PDF and TXT reports."
    )
    parser.add_argument("notebook", help="Path to the input Jupyter Notebook (.ipynb)")
    parser.add_argument(
        "--pdf", help="Custom path for the output PDF file", default=None
    )
    parser.add_argument(
        "--txt", help="Custom path for the output TXT file", default=None
    )
    parser.add_argument(
        "--model",
        help="Local Ollama model to use, or 'auto' to let the agent decide (default: auto)",
        default="auto",
    )

    args = parser.parse_args()

    input_path = args.notebook
    if not os.path.exists(input_path):
        print(f"Error: File '{input_path}' not found.")
        sys.exit(1)

    pdf_dir = "pdf_reports"
    txt_dir = "txt_reports"
    os.makedirs(pdf_dir, exist_ok=True)
    os.makedirs(txt_dir, exist_ok=True)

    base_name = os.path.basename(input_path).replace(".ipynb", "")
    output_pdf_path = (
        args.pdf if args.pdf else os.path.join(pdf_dir, f"{base_name}_report.pdf")
    )
    output_txt_path = (
        args.txt if args.txt else os.path.join(txt_dir, f"{base_name}_flow.txt")
    )

    build_agent_report(input_path, output_pdf_path, output_txt_path, args.model)
