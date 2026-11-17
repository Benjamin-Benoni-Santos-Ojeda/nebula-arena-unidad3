import os
import re
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
)
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super(NumberedCanvas, self).__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_footer(num_pages)
            super(NumberedCanvas, self).showPage()
        super(NumberedCanvas, self).save()

    def draw_footer(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 9)
        self.setFillColor(colors.HexColor("#475569"))
        self.drawString(40, 25, "Nebula Arena · Unidad 3 (Videojuegos en la Nube) — Presentación de 10 minutos")
        self.drawRightString(752, 25, f"Diapositiva {self._pageNumber} de {page_count} · Benjamin Santos (25460724)")
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.5)
        self.line(40, 38, 752, 38)
        self.restoreState()

def build_slides():
    desktop = os.path.expanduser('~/Desktop')
    out_pdf = os.path.join(desktop, 'Diapositivas_Presentacion_10min.pdf')
    
    doc = SimpleDocTemplate(
        out_pdf,
        pagesize=landscape(letter),
        leftMargin=40,
        rightMargin=40,
        topMargin=35,
        bottomMargin=45
    )

    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'SlideTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#1e3a8a"),
        spaceAfter=6
    )
    
    subtitle_style = ParagraphStyle(
        'SlideSubtitle',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#0284c7"),
        spaceAfter=12
    )

    body_style = ParagraphStyle(
        'SlideBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14.5,
        textColor=colors.HexColor("#1e293b"),
        spaceAfter=5
    )

    bullet_style = ParagraphStyle(
        'SlideBullet',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=14,
        textColor=colors.HexColor("#1e293b"),
        leftIndent=15,
        spaceAfter=4
    )

    code_style = ParagraphStyle(
        'SlideCode',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#0f172a"),
        leftIndent=20,
        spaceAfter=4
    )

    story = []

    # Read Guion-presentacion.md
    with open('Guion-presentacion.md', 'r', encoding='utf-8') as f:
        content = f.read()

    slides = content.split('---')
    valid_slides = [s.strip() for s in slides if s.strip() and not s.strip().startswith('marp:')]

    for idx, s in enumerate(valid_slides):
        lines = s.split('\n')
        for line in lines:
            line_str = line.strip()
            if not line_str:
                story.append(Spacer(1, 4))
                continue
            if line_str.startswith('# '):
                story.append(Paragraph(line_str[2:].replace('**', '<b>').replace('**', '</b>'), title_style))
            elif line_str.startswith('## '):
                story.append(Paragraph(line_str[3:].replace('**', '<b>').replace('**', '</b>'), title_style))
            elif line_str.startswith('### '):
                story.append(Paragraph(line_str[4:].replace('**', '<b>').replace('**', '</b>'), subtitle_style))
            elif line_str.startswith('- ') or line_str.startswith('* '):
                text = line_str[2:]
                text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
                text = re.sub(r'`(.*?)`', r'<font color="#b91c1c" face="Courier">\1</font>', text)
                text = re.sub(r'\[(.*?)\]\(.*?\)', r'<u>\1</u>', text)
                story.append(Paragraph(f"• {text}", bullet_style))
            elif line_str.startswith('  - ') or line_str.startswith('    - '):
                text = line_str.lstrip(' -*')
                text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
                text = re.sub(r'`(.*?)`', r'<font color="#b91c1c" face="Courier">\1</font>', text)
                text = re.sub(r'\[(.*?)\]\(.*?\)', r'<u>\1</u>', text)
                sub_bullet = ParagraphStyle('SubBullet', parent=bullet_style, leftIndent=30)
                story.append(Paragraph(f"– {text}", sub_bullet))
            elif '|' in line_str:
                # Table or pipe
                continue
            else:
                text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', line_str)
                text = re.sub(r'`(.*?)`', r'<font color="#b91c1c" face="Courier">\1</font>', text)
                story.append(Paragraph(text, body_style))
        
        if idx < len(valid_slides) - 1:
            story.append(PageBreak())

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Diapositivas PDF generadas exitosamente en: {out_pdf}")

if __name__ == '__main__':
    build_slides()
