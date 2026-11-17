import os
import markdown
import shutil

md_path = 'Guion-presentacion.md'
with open(md_path, 'r', encoding='utf-8') as f:
    text = f.read()

slides_raw = text.split('---')
slides = [s.strip() for s in slides_raw if s.strip() and not s.strip().startswith('marp:')]

html_slides = []
for i, slide in enumerate(slides):
    html_content = markdown.markdown(slide, extensions=['tables', 'fenced_code'])
    html_slides.append(f"""
    <section class="slide" id="slide-{i+1}">
        <div class="slide-header">
            <span class="badge">Diapositiva {i+1} de {len(slides)}</span>
            <span class="sub">Nebula Arena · Unidad 3</span>
        </div>
        <div class="slide-body">{html_content}</div>
        <div class="slide-footer">Benjamin Benoni Santos Ojeda (25460724) · M.C. Omar Joel · TecNM Colima</div>
    </section>
    """)

slides_joined = "\n".join(html_slides)

full_html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Nebula Arena - Diapositivas de Presentación (10 min)</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            background: #0f172a;
            color: #f8fafc;
            font-family: 'Inter', sans-serif;
            padding: 20px;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 25px;
        }}
        .controls {{
            position: sticky;
            top: 10px;
            background: rgba(30, 41, 59, 0.95);
            backdrop-filter: blur(8px);
            padding: 10px 20px;
            border-radius: 999px;
            border: 1px solid #334155;
            display: flex;
            gap: 15px;
            z-index: 100;
        }}
        .controls button {{
            background: #3b82f6;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 6px;
            font-weight: 600;
            cursor: pointer;
        }}
        .controls button:hover {{ background: #2563eb; }}
        .slide {{
            background: #1e293b;
            width: 100%;
            max-width: 960px;
            min-height: 540px;
            border-radius: 12px;
            border: 1px solid #334155;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5);
            padding: 35px 45px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            page-break-after: always;
        }}
        .slide-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid #334155;
            padding-bottom: 12px;
            margin-bottom: 20px;
        }}
        .badge {{ background: #3b82f6; color: white; padding: 3px 10px; border-radius: 12px; font-size: 12px; font-weight: 700; }}
        .sub {{ font-size: 12px; color: #94a3b8; }}
        .slide-body h1 {{ font-size: 24px; color: #60a5fa; margin-bottom: 15px; }}
        .slide-body h2 {{ font-size: 20px; color: #38bdf8; margin-bottom: 15px; border-bottom: 1px solid #334155; padding-bottom: 8px; }}
        .slide-body h3 {{ font-size: 15px; color: #94a3b8; margin-bottom: 15px; }}
        .slide-body p, .slide-body li {{ font-size: 14px; line-height: 1.6; color: #cbd5e1; }}
        .slide-body ul {{ margin-left: 20px; margin-bottom: 12px; }}
        .slide-body li {{ margin-bottom: 6px; }}
        .slide-body strong {{ color: #ffffff; }}
        .slide-body code {{ background: #0f172a; color: #f43f5e; padding: 2px 6px; border-radius: 4px; font-family: 'JetBrains Mono', monospace; font-size: 12px; }}
        .slide-body table {{ width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 13px; }}
        .slide-body th, .slide-body td {{ border: 1px solid #334155; padding: 8px 12px; text-align: left; }}
        .slide-body th {{ background: #0f172a; color: #38bdf8; }}
        .slide-footer {{
            border-top: 1px solid #334155;
            padding-top: 12px;
            margin-top: 20px;
            font-size: 11px;
            color: #64748b;
            text-align: right;
        }}
        @media print {{
            body {{ background: white; padding: 0; }}
            .controls {{ display: none; }}
            .slide {{ background: white; color: black; border: none; box-shadow: none; max-width: 100%; height: 100vh; page-break-after: always; padding: 30px; }}
            .slide-body h1, .slide-body h2 {{ color: #1e3a8a; }}
            .slide-body p, .slide-body li {{ color: #1e293b; }}
            .slide-body strong {{ color: #000; }}
            .slide-body code {{ background: #f1f5f9; color: #b91c1c; }}
            .slide-body th {{ background: #f1f5f9; color: #1e3a8a; }}
        }}
    </style>
</head>
<body>
    <div class="controls">
        <button onclick="window.print()">🖨️ Imprimir / Guardar Diapositivas como PDF</button>
    </div>
    {slides_joined}
</body>
</html>
"""

desktop = os.path.expanduser('~/Desktop')
out_path = os.path.join(desktop, 'Diapositivas_Presentacion_10min.html')
with open(out_path, 'w', encoding='utf-8') as f:
    f.write(full_html)

shutil.copy(out_path, 'Diapositivas_Presentacion_10min.html')
print(f"Diapositivas generadas exitosamente en: {out_path}")
