import sys
import os
import re
import requests
import nbformat
import markdown
from pygments import highlight
from pygments.lexers import PythonLexer
from pygments.formatters import HtmlFormatter
from weasyprint import HTML


def get_ollama_clarification(code, error_text="", model_name="llama3.2"):
    """Queries the local Ollama instance for code clarification/error fixing."""
    prompt = f"Analyze this Python data science code:\n\n{code}\n\n"
    if error_text:
        prompt += f"The code resulted in this error:\n{error_text}\n\nExplain exactly why this error happened and how to fix it in 2-3 sentences."
    else:
        prompt += "Explain what this specific code snippet is doing conceptually in 2-3 sentences."

    url = "http://localhost:11434/api/generate"
    payload = {"model": model_name, "prompt": prompt, "stream": False}

    try:
        response = requests.post(
            url, json=payload, timeout=60
        )  # 60 sec timeout for generation
        response.raise_for_status()
        return response.json().get("response", "")
    except requests.exceptions.ConnectionError:
        return "*AI Clarification unavailable: Could not connect to Ollama. Make sure Ollama is installed and running locally.*"
    except Exception as e:
        return f"*AI Clarification error: {str(e)}*"


def clean_ansi(text):
    """Removes ANSI escape codes from terminal outputs/errors."""
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi_escape.sub("", text)


def build_agent_report(notebook_path, output_pdf_path):
    print(f"[*] Agent reading notebook: {notebook_path}")

    with open(notebook_path, "r", encoding="utf-8") as f:
        nb = nbformat.read(f, as_version=4)

    toc_items = []
    html_cells = []

    pygments_formatter = HtmlFormatter(style="default", cssclass="syntax-highlight")
    css_syntax = pygments_formatter.get_style_defs()

    print("[*] Processing cells and requesting local AI analysis...")
    for i, cell in enumerate(nb.cells):
        if cell.cell_type == "markdown":
            # Extract headers for TOC
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
            html_cells.append(f'<div class="markdown-block">{md_html}</div>')

        elif cell.cell_type == "code":
            # 1. Extract the code and check for errors
            code_text = cell.source
            error_text = ""
            if cell.outputs:
                for output in cell.outputs:
                    if output.output_type == "error":
                        error_text = clean_ansi("\n".join(output.traceback))

            # 2. ASK OLLAMA TO CLARIFY
            # Skip AI for completely empty code cells
            if code_text.strip():
                print(f"    -> Querying Ollama for Cell {i + 1}...")
                ai_explanation = get_ollama_clarification(code_text, error_text)
                ai_html = markdown.markdown(
                    f"**🤖 Local AI Analysis:**\n{ai_explanation}"
                )
                cell_content = f'<div class="ai-clarification">{ai_html}</div>'
            else:
                cell_content = ""

            # 3. Add Syntax Highlighting
            code_html = highlight(code_text, PythonLexer(), pygments_formatter)
            cell_content += f'<div class="code-block">{code_html}</div>'

            # 4. Parse Outputs Safely
            if cell.outputs:
                cell_content += '<div class="output-block">'
                for output in cell.outputs:
                    if output.output_type == "stream":
                        cell_content += f'<pre class="output-stream">{clean_ansi(output.text)}</pre>'
                    elif output.output_type in ["execute_result", "display_data"]:
                        data = output.data
                        if "text/html" in data:
                            cell_content += (
                                f'<div class="output-html">{data["text/html"]}</div>'
                            )
                        elif "image/svg+xml" in data:
                            cell_content += (
                                f'<div class="output-svg">{data["image/svg+xml"]}</div>'
                            )
                        elif "image/png" in data:
                            cell_content += f'<img class="output-image" src="data:image/png;base64,{data["image/png"]}" alt="PNG Output"/>'
                        elif "image/jpeg" in data:
                            cell_content += f'<img class="output-image" src="data:image/jpeg;base64,{data["image/jpeg"]}" alt="JPEG Output"/>'
                        elif "text/plain" in data:
                            cell_content += (
                                f'<pre class="output-plain">{data["text/plain"]}</pre>'
                            )

                    elif output.output_type == "error":
                        traceback_text = clean_ansi("\n".join(output.traceback))
                        cell_content += (
                            f'<pre class="output-error">{traceback_text}</pre>'
                        )
                cell_content += "</div>"
            html_cells.append(cell_content)

    # Smart TOC Fallback
    print("[*] Assembling Document Structure...")
    if len(toc_items) > 0:
        toc_html = (
            "<div class='toc-container'><h2>Table of Contents</h2><ul class='toc-list'>"
        )
        for item in toc_items:
            indent_class = f"toc-level-{item['level']}"
            toc_html += f"<li class='{indent_class}'><a href='#{item['anchor']}'>{item['title']}</a></li>"
        toc_html += "</ul></div><div class='page-break'></div>"
    else:
        toc_html = "<div class='toc-container'><h2>Report Content</h2><p style='color: #666;'>No structural headers found. Proceeding directly to code execution logs.</p></div><div class='page-break'></div>"

    # Assemble Master HTML
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
            .toc-container {{ margin-bottom: 30px; }}
            .toc-list {{ list-style-type: none; padding-left: 0; }}
            .toc-level-1 {{ font-weight: bold; margin-top: 10px; }}
            .toc-level-2 {{ margin-left: 20px; }}
            .ai-clarification {{ background-color: #f3e8fa; padding: 12px; border-radius: 6px; margin-bottom: 8px; border-left: 4px solid #8e44ad; font-size: 10pt; }}
            .code-block {{ background-color: #f8f9fa; border: 1px solid #e9ecef; border-radius: 4px; padding: 10px; margin-bottom: 5px; font-family: 'Courier New', monospace; font-size: 9pt; overflow-x: auto; }}
            .output-block {{ background-color: #ffffff; border-left: 4px solid #007bff; padding: 10px; margin-bottom: 20px; font-size: 9pt; }}
            .output-stream, .output-plain, .output-error {{ white-space: pre-wrap; font-family: 'Courier New', monospace; margin: 0; }}
            .output-error {{ color: #dc3545; }}
            .output-image, .output-svg svg {{ max-width: 100%; height: auto; margin-top: 10px; }}
            table {{ border-collapse: collapse; width: 100%; margin-bottom: 15px; font-size: 9pt; }}
            th, td {{ border: 1px solid #ddd; padding: 6px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
        </style>
    </head>
    <body>
        {toc_html}
        {"".join(html_cells)}
    </body>
    </html>
    """

    print("[*] Rendering professional PDF (this may take a moment)...")
    HTML(string=master_html).write_pdf(output_pdf_path)
    print(f"[+] Success! PDF generated at: {output_pdf_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(
            "Usage: python nb2pdf_agent.py <path_to_notebook.ipynb> [output_path.pdf]"
        )
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = (
        sys.argv[2]
        if len(sys.argv) > 2
        else input_path.replace(".ipynb", "_report.pdf")
    )

    if not os.path.exists(input_path):
        print(f"Error: File '{input_path}' not found.")
        sys.exit(1)

    build_agent_report(input_path, output_path)
