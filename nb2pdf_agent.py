import sys
import os
import re
import nbformat
import markdown
from pygments import highlight
from pygments.lexers import PythonLexer
from pygments.formatters import HtmlFormatter
from weasyprint import HTML, CSS


def clean_ansi(text):
    """Removes ANSI escape codes from terminal outputs/errors."""
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi_escape.sub("", text)


def build_agent_report(notebook_path, output_pdf_path):
    print(f"[*] Agent reading notebook: {notebook_path}")

    # 1. Parse Notebook JSON safely
    with open(notebook_path, "r", encoding="utf-8") as f:
        nb = nbformat.read(f, as_version=4)

    toc_items = []
    html_cells = []

    # 2. Setup Pygments for Code Formatting
    pygments_formatter = HtmlFormatter(style="default", cssclass="syntax-highlight")
    css_syntax = pygments_formatter.get_style_defs()

    # 3. Iterate through cells and extract components
    print("[*] Processing cells (Markdown, Code, Outputs)...")
    for cell in nb.cells:
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

            # Convert Markdown to HTML
            md_html = markdown.markdown(
                cell.source, extensions=["tables", "fenced_code", "toc"]
            )
            html_cells.append(f'<div class="markdown-block">{md_html}</div>')

        elif cell.cell_type == "code":
            # Apply Syntax Highlighting
            code_html = highlight(cell.source, PythonLexer(), pygments_formatter)
            cell_content = f'<div class="code-block">{code_html}</div>'

            # Parse Outputs
            if cell.outputs:
                cell_content += '<div class="output-block">'
                for output in cell.outputs:
                    if output.output_type == "stream":
                        clean_text = clean_ansi(output.text)
                        cell_content += f'<pre class="output-stream">{clean_text}</pre>'

                    elif output.output_type in ["execute_result", "display_data"]:
                        data = output.data
                        if "text/html" in data:
                            cell_content += (
                                f'<div class="output-html">{data["text/html"]}</div>'
                            )
                        elif "image/png" in data:
                            cell_content += f'<img class="output-image" src="data:image/png;base64,{data["image/png"]}" alt="Cell Output Image"/>'
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

    # 4. Build Table of Contents HTML
    print("[*] Assembling Table of Contents...")
    toc_html = (
        "<div class='toc-container'><h2>Table of Contents</h2><ul class='toc-list'>"
    )
    for item in toc_items:
        indent_class = f"toc-level-{item['level']}"
        toc_html += f"<li class='{indent_class}'><a href='#{item['anchor']}'>{item['title']}</a></li>"
    toc_html += "</ul></div><div class='page-break'></div>"

    # 5. Assemble Master HTML Document
    master_html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Report</title>
        <style>
            {css_syntax}
            
            /* Professional Print CSS */
            @page {{
                size: A4;
                margin: 2cm;
                @bottom-right {{
                    content: "Page " counter(page) " of " counter(pages);
                    font-family: Arial, sans-serif;
                    font-size: 9pt;
                    color: #666;
                }}
                @top-left {{
                    content: "Automated AI Analysis Report";
                    font-family: Arial, sans-serif;
                    font-size: 9pt;
                    color: #999;
                }}
            }}
            body {{
                font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                font-size: 11pt;
            }}
            h1, h2, h3 {{ color: #2c3e50; }}
            .page-break {{ page-break-after: always; }}
            
            /* TOC Styles */
            .toc-container {{ margin-bottom: 30px; }}
            .toc-list {{ list-style-type: none; padding-left: 0; }}
            .toc-level-1 {{ font-weight: bold; margin-top: 10px; }}
            .toc-level-2 {{ margin-left: 20px; }}
            .toc-level-3 {{ margin-left: 40px; font-size: 0.9em; }}
            .toc-list a {{ text-decoration: none; color: #34495e; }}
            
            /* Cell Styles */
            .markdown-block {{ margin-bottom: 20px; }}
            .code-block {{
                background-color: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 4px;
                padding: 10px;
                margin-bottom: 5px;
                font-family: 'Courier New', Courier, monospace;
                font-size: 9pt;
                overflow-x: auto;
            }}
            .output-block {{
                background-color: #ffffff;
                border-left: 4px solid #007bff;
                padding: 10px;
                margin-bottom: 20px;
                font-size: 9pt;
            }}
            .output-stream, .output-plain {{
                white-space: pre-wrap;
                font-family: 'Courier New', Courier, monospace;
            }}
            .output-error {{
                color: #dc3545;
                white-space: pre-wrap;
                font-family: 'Courier New', Courier, monospace;
            }}
            .output-image {{ max-width: 100%; height: auto; }}
            
            /* Pandas HTML Table Styling */
            table {{
                border-collapse: collapse;
                width: 100%;
                margin-bottom: 15px;
                font-size: 9pt;
            }}
            th, td {{
                border: 1px solid #ddd;
                padding: 6px;
                text-align: left;
            }}
            th {{ background-color: #f2f2f2; }}
        </style>
    </head>
    <body>
        {toc_html}
        {"".join(html_cells)}
    </body>
    </html>
    """

    # 6. Render PDF
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
