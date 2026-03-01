import argparse
import os
import json
import re
from pathlib import Path
from datetime import datetime

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    PageBreak,
    Table,
    TableStyle,
    KeepTogether,
    Frame,
    FrameBreak,
    PageTemplate,
    NextPageTemplate,
    Indenter,
    HRFlowable,
    Image as RLImage,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, inch
from reportlab.lib.colors import HexColor, Color, black, white, grey
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfgen import canvas
from reportlab.platypus.tableofcontents import TableOfContents


# =========================
# ADVANCED PAGE TEMPLATES
# =========================

class NumberedCanvas(canvas.Canvas):
    """Custom canvas with headers, footers, and page numbers"""
    
    def __init__(self, *args, **kwargs):
        canvas.Canvas.__init__(self, *args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_decorations(self, page_count):
        self.saveState()
        
        # Header line
        self.setStrokeColor(HexColor("#2C3E50"))
        self.setLineWidth(2)
        self.line(20*mm, A4[1] - 15*mm, A4[0] - 20*mm, A4[1] - 15*mm)
        
        # Footer
        self.setFont('Helvetica', 9)
        self.setFillColor(grey)
        
        # Page number
        page_num_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(A4[0] - 20*mm, 15*mm, page_num_text)
        
        # Document info
        self.drawString(20*mm, 15*mm, f"Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        
        # Footer line
        self.setStrokeColor(HexColor("#BDC3C7"))
        self.setLineWidth(1)
        self.line(20*mm, 18*mm, A4[0] - 20*mm, 18*mm)
        
        self.restoreState()


# =========================
# COMPREHENSIVE STYLES
# =========================

def build_styles():
    """Create comprehensive style palette"""
    styles = getSampleStyleSheet()
    
    # Color palette
    primary = HexColor("#2C3E50")
    secondary = HexColor("#3498DB")
    accent = HexColor("#E74C3C")
    success = HexColor("#27AE60")
    code_bg = HexColor("#F8F9FA")
    code_border = HexColor("#DEE2E6")
    
    # Title styles
    styles.add(ParagraphStyle(
        name="DocumentTitle",
        parent=styles['Heading1'],
        fontSize=28,
        leading=34,
        textColor=primary,
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    ))
    
    styles.add(ParagraphStyle(
        name="ReportSubtitle",
        fontSize=14,
        leading=18,
        textColor=secondary,
        spaceAfter=20,
        alignment=TA_CENTER,
        fontName='Helvetica-Oblique'
    ))
    
    # Heading hierarchy
    styles.add(ParagraphStyle(
        name="Heading1Custom",
        parent=styles['Heading1'],
        fontSize=18,
        leading=22,
        textColor=primary,
        spaceBefore=16,
        spaceAfter=10,
        borderPadding=3,
        leftIndent=0,
        fontName='Helvetica-Bold',
        keepWithNext=True
    ))
    
    styles.add(ParagraphStyle(
        name="Heading2Custom",
        parent=styles['Heading2'],
        fontSize=14,
        leading=18,
        textColor=secondary,
        spaceBefore=12,
        spaceAfter=8,
        leftIndent=0,
        fontName='Helvetica-Bold',
        keepWithNext=True
    ))
    
    styles.add(ParagraphStyle(
        name="Heading3Custom",
        parent=styles['Heading3'],
        fontSize=12,
        leading=16,
        textColor=HexColor("#34495E"),
        spaceBefore=10,
        spaceAfter=6,
        leftIndent=0,
        fontName='Helvetica-Bold',
        keepWithNext=True
    ))
    
    # Body text variants
    styles.add(ParagraphStyle(
        name="BodyJustified",
        parent=styles['BodyText'],
        fontSize=10,
        leading=14,
        alignment=TA_JUSTIFY,
        spaceAfter=8
    ))
    
    styles.add(ParagraphStyle(
        name="BodyIndented",
        parent=styles['BodyText'],
        fontSize=10,
        leading=14,
        leftIndent=20,
        spaceAfter=8
    ))
    
    # Code and preformatted
    styles.add(ParagraphStyle(
        name="CodeBlock",
        fontName="Courier",
        fontSize=8,
        leading=10,
        textColor=HexColor("#212529"),
        backColor=code_bg,
        borderColor=code_border,
        borderWidth=1,
        borderPadding=8,
        leftIndent=10,
        rightIndent=10,
        spaceBefore=10,
        spaceAfter=10
    ))
    
    styles.add(ParagraphStyle(
        name="InlineCode",
        parent=styles['BodyText'],
        fontName="Courier",
        fontSize=9,
        textColor=accent,
        backColor=code_bg
    ))
    
    # Special blocks
    styles.add(ParagraphStyle(
        name="BlockQuote",
        parent=styles['BodyText'],
        fontSize=10,
        leading=14,
        leftIndent=30,
        rightIndent=30,
        textColor=HexColor("#6C757D"),
        borderColor=secondary,
        borderWidth=2,
        borderPadding=10,
        spaceBefore=10,
        spaceAfter=10,
        fontName='Helvetica-Oblique'
    ))
    
    styles.add(ParagraphStyle(
        name="CalloutBox",
        parent=styles['BodyText'],
        fontSize=10,
        leading=14,
        backColor=HexColor("#E8F4F8"),
        borderColor=secondary,
        borderWidth=1,
        borderPadding=12,
        spaceBefore=12,
        spaceAfter=12
    ))
    
    styles.add(ParagraphStyle(
        name="WarningBox",
        parent=styles['BodyText'],
        fontSize=10,
        leading=14,
        backColor=HexColor("#FFF3CD"),
        borderColor=HexColor("#FFC107"),
        borderWidth=2,
        borderPadding=12,
        spaceBefore=12,
        spaceAfter=12
    ))
    
    # Lists
    styles.add(ParagraphStyle(
        name="BulletItem",
        parent=styles['BodyText'],
        fontSize=10,
        leading=14,
        leftIndent=20,
        bulletIndent=10,
        spaceAfter=4
    ))
    
    styles.add(ParagraphStyle(
        name="NumberedItem",
        parent=styles['BodyText'],
        fontSize=10,
        leading=14,
        leftIndent=25,
        bulletIndent=10,
        spaceAfter=4
    ))
    
    # Metadata and captions
    styles.add(ParagraphStyle(
        name="Metadata",
        fontSize=9,
        leading=12,
        textColor=grey,
        spaceAfter=6,
        fontName='Helvetica-Oblique'
    ))
    
    styles.add(ParagraphStyle(
        name="Caption",
        fontSize=9,
        leading=11,
        textColor=HexColor("#6C757D"),
        alignment=TA_CENTER,
        spaceAfter=12,
        fontName='Helvetica-Oblique'
    ))
    
    styles.add(ParagraphStyle(
        name="TOCHeading",
        fontSize=16,
        leading=20,
        textColor=primary,
        spaceAfter=16,
        fontName='Helvetica-Bold'
    ))
    
    return styles


# =========================
# TABLE STYLES
# =========================

def get_table_style_basic():
    """Basic table style"""
    return TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#3498DB')),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('TOPPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), white),
        ('GRID', (0, 0), (-1, -1), 1, HexColor('#BDC3C7')),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, HexColor('#F8F9FA')]),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ])


def get_table_style_minimal():
    """Minimal table style"""
    return TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('LINEBELOW', (0, 0), (-1, 0), 2, HexColor('#2C3E50')),
        ('LINEBELOW', (0, 1), (-1, -1), 0.5, HexColor('#DEE2E6')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ])


# =========================
# MARKDOWN PARSER
# =========================

class AdvancedMarkdownParser:
    """Parse markdown into ReportLab flowables with rich formatting"""
    
    def __init__(self, styles):
        self.styles = styles
        
    def parse(self, md_text):
        """Parse markdown text into flowables"""
        flowables = []
        lines = md_text.split('\n')
        
        i = 0
        in_code_block = False
        code_block_lines = []
        in_list = False
        list_items = []
        
        while i < len(lines):
            line = lines[i]
            
            # Code blocks
            if line.strip().startswith('```'):
                if in_code_block:
                    # End code block
                    code_text = '\n'.join(code_block_lines)
                    flowables.append(self._create_code_block(code_text))
                    code_block_lines = []
                    in_code_block = False
                else:
                    # Start code block
                    in_code_block = True
                i += 1
                continue
            
            if in_code_block:
                code_block_lines.append(line)
                i += 1
                continue
            
            # Headers
            if line.startswith('# '):
                flowables.append(Paragraph(line[2:], self.styles['Heading1Custom']))
                flowables.append(HRFlowable(width="100%", thickness=1, color=HexColor("#3498DB"), spaceAfter=10))
            elif line.startswith('## '):
                flowables.append(Paragraph(line[3:], self.styles['Heading2Custom']))
            elif line.startswith('### '):
                flowables.append(Paragraph(line[4:], self.styles['Heading3Custom']))
            
            # Horizontal rule
            elif line.strip() in ['---', '***', '___']:
                flowables.append(HRFlowable(width="80%", thickness=1, color=HexColor("#BDC3C7"), 
                                           spaceBefore=10, spaceAfter=10))
            
            # Block quotes
            elif line.strip().startswith('>'):
                quote_text = line.strip()[1:].strip()
                flowables.append(Paragraph(quote_text, self.styles['BlockQuote']))
            
            # Unordered lists
            elif line.strip().startswith(('- ', '* ', '+ ')):
                item_text = line.strip()[2:]
                flowables.append(Paragraph(f"• {item_text}", self.styles['BulletItem']))
            
            # Ordered lists
            elif re.match(r'^\d+\.\s', line.strip()):
                match = re.match(r'^(\d+)\.\s(.+)', line.strip())
                if match:
                    num, text = match.groups()
                    flowables.append(Paragraph(f"{num}. {text}", self.styles['NumberedItem']))
            
            # Tables (simple detection)
            elif '|' in line and line.strip().startswith('|'):
                table_lines = [line]
                i += 1
                while i < len(lines) and '|' in lines[i]:
                    table_lines.append(lines[i])
                    i += 1
                i -= 1
                flowables.extend(self._create_table(table_lines))
            
            # Regular paragraph
            elif line.strip():
                # Apply inline formatting
                formatted_text = self._apply_inline_formatting(line)
                flowables.append(Paragraph(formatted_text, self.styles['BodyJustified']))
            
            # Empty line
            else:
                flowables.append(Spacer(1, 6))
            
            i += 1
        
        return flowables
    
    def _create_code_block(self, code_text):
        """Create formatted code block"""
        # Escape HTML entities
        code_text = code_text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        return Paragraph(f'<pre>{code_text}</pre>', self.styles['CodeBlock'])
    
    def _create_table(self, table_lines):
        """Create table from markdown table lines"""
        flowables = []
        
        # Parse table
        rows = []
        for line in table_lines:
            # Skip separator line
            if re.match(r'^\|[\s\-:]+\|$', line.strip()):
                continue
            
            cells = [cell.strip() for cell in line.split('|')[1:-1]]
            if cells:
                rows.append(cells)
        
        if rows:
            # Convert to Paragraphs for wrapping
            data = []
            for i, row in enumerate(rows):
                style = self.styles['Heading3Custom'] if i == 0 else self.styles['BodyText']
                data.append([Paragraph(cell, style) for cell in row])
            
            # Create table
            col_widths = [A4[0] / len(rows[0]) - 40*mm/len(rows[0])] * len(rows[0])
            table = Table(data, colWidths=col_widths, repeatRows=1)
            table.setStyle(get_table_style_basic())
            
            flowables.append(Spacer(1, 10))
            flowables.append(table)
            flowables.append(Spacer(1, 10))
        
        return flowables
    
    def _apply_inline_formatting(self, text):
        """Apply inline markdown formatting"""
        # Bold
        text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
        text = re.sub(r'__(.+?)__', r'<b>\1</b>', text)
        
        # Italic
        text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
        text = re.sub(r'_(.+?)_', r'<i>\1</i>', text)
        
        # Inline code
        text = re.sub(r'`(.+?)`', r'<font name="Courier" color="#E74C3C">\1</font>', text)
        
        # Links
        text = re.sub(r'\[(.+?)\]\((.+?)\)', r'<link href="\2" color="blue"><u>\1</u></link>', text)
        
        return text


# =========================
# JSON PARSER
# =========================

def parse_json_advanced(json_text, styles):
    """Parse JSON with syntax highlighting and structure"""
    flowables = []
    
    try:
        data = json.loads(json_text)
        
        # Create metadata header
        flowables.append(Paragraph("JSON Document", styles['Heading2Custom']))
        flowables.append(Spacer(1, 10))
        
        # If it's a structured object, create a table
        if isinstance(data, dict) and len(data) < 50:
            table_data = [
                [Paragraph('<b>Key</b>', styles['BodyText']), 
                 Paragraph('<b>Value</b>', styles['BodyText'])]
            ]
            
            for key, value in data.items():
                value_str = json.dumps(value, indent=2) if isinstance(value, (dict, list)) else str(value)
                table_data.append([
                    Paragraph(f'<font name="Courier">{key}</font>', styles['BodyText']),
                    Paragraph(f'<font name="Courier" size="8">{value_str}</font>', styles['BodyText'])
                ])
            
            table = Table(table_data, colWidths=[60*mm, 110*mm])
            table.setStyle(get_table_style_minimal())
            flowables.append(table)
        else:
            # Fallback to formatted code block
            pretty = json.dumps(data, indent=2)
            flowables.append(Paragraph(f'<pre>{pretty}</pre>', styles['CodeBlock']))
    
    except Exception:
        # Invalid JSON, display as-is
        flowables.append(Paragraph("Raw JSON (Invalid)", styles['Heading3Custom']))
        flowables.append(Paragraph(f'<pre>{json_text}</pre>', styles['CodeBlock']))
    
    return flowables


# =========================
# TEXT PARSER
# =========================

def parse_text_advanced(text, styles):
    """Parse plain text with intelligent formatting"""
    flowables = []
    
    lines = text.split('\n')
    current_paragraph = []
    
    for line in lines:
        # Detect code-like content
        if re.match(r'^[\s]*[\w]+\s*[=:]\s*.+', line) or line.strip().startswith(('#', '//', '--', '/*')):
            # Flush current paragraph
            if current_paragraph:
                flowables.append(Paragraph(' '.join(current_paragraph), styles['BodyJustified']))
                current_paragraph = []
            
            # Add as code
            flowables.append(Paragraph(f'<font name="Courier">{line}</font>', styles['CodeBlock']))
        
        # Empty line - paragraph break
        elif not line.strip():
            if current_paragraph:
                flowables.append(Paragraph(' '.join(current_paragraph), styles['BodyJustified']))
                current_paragraph = []
            flowables.append(Spacer(1, 6))
        
        # Regular text
        else:
            current_paragraph.append(line)
    
    # Flush remaining
    if current_paragraph:
        flowables.append(Paragraph(' '.join(current_paragraph), styles['BodyJustified']))
    
    return flowables


# =========================
# FILE ROUTER
# =========================

def build_story_from_file(file_path, styles):
    """Build comprehensive document story"""
    ext = os.path.splitext(file_path)[1].lower()
    
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    story = []
    
    # Cover page
    story.append(Spacer(1, 80))
    story.append(Paragraph(os.path.basename(file_path), styles["DocumentTitle"]))
    story.append(Paragraph(
        f"Document Type: {ext.upper()[1:] if ext else 'TEXT'}", 
        styles["ReportSubtitle"]
    ))
    story.append(Spacer(1, 20))
    
    # Metadata box
    metadata_content = f"""
    <b>Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br/>
    <b>File Size:</b> {len(content):,} bytes<br/>
    <b>Lines:</b> {len(content.splitlines()):,}
    """
    story.append(Paragraph(metadata_content, styles["CalloutBox"]))
    
    story.append(PageBreak())
    
    # Content based on type
    if ext == ".md":
        parser = AdvancedMarkdownParser(styles)
        story.extend(parser.parse(content))
    
    elif ext == ".json":
        story.extend(parse_json_advanced(content, styles))
    
    else:
        story.append(Paragraph("Document Content", styles['Heading1Custom']))
        story.append(HRFlowable(width="100%", thickness=2, color=HexColor("#2C3E50"), spaceAfter=15))
        story.extend(parse_text_advanced(content, styles))
    
    return story


# =========================
# PDF BUILDER
# =========================

def generate_pdf(story, output_pdf_path):
    """Generate PDF with advanced formatting"""
    doc = SimpleDocTemplate(
        output_pdf_path,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=25 * mm,
        bottomMargin=25 * mm,
        title="Professional Document",
        author="PDF Generator"
    )
    
    doc.build(story, canvasmaker=NumberedCanvas)


def generate_pdf_from_file(input_path, output_path=None):
    """Headless entrypoint for converting a supported text file into a PDF."""
    source = Path(input_path)
    if not source.exists():
        raise FileNotFoundError(f"Input file not found: {source}")

    if output_path is None:
        output = source.with_name(source.name.replace(".", "_") + ".pdf")
    else:
        output = Path(output_path)
        if output.suffix.lower() != ".pdf":
            output = output.with_suffix(".pdf")

    output.parent.mkdir(parents=True, exist_ok=True)

    styles = build_styles()
    story = build_story_from_file(str(source), styles)
    generate_pdf(story, str(output))
    return output


# =========================
# OPTIONAL KIVY UI
# =========================
def create_pdf_generator_app(initial_input=None, initial_output=None):
    try:
        from kivy.app import App
        from kivy.uix.boxlayout import BoxLayout
        from kivy.uix.button import Button
        from kivy.uix.label import Label
        from kivy.uix.filechooser import FileChooserListView
        from kivy.uix.popup import Popup
        from kivy.metrics import dp
    except ImportError as exc:
        raise RuntimeError("Kivy is not installed. Install the 'pdf-gui' extra to use GUI mode.") from exc

    class PDFGeneratorApp(App):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.input_file = initial_input
            self.output_folder = None
            self.output_pdf_path = initial_output

        def build(self):
            self.title = "PDF Generator Pro"
            layout = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))

            self.status_label = Label(
                text='Select input file and output folder',
                size_hint_y=0.15,
                font_size=dp(16)
            )
            layout.add_widget(self.status_label)

            input_btn = Button(text='Select Input File', size_hint_y=0.15, font_size=dp(18))
            input_btn.bind(on_press=self.show_input_picker)
            layout.add_widget(input_btn)

            output_btn = Button(text='Select Output Folder', size_hint_y=0.15, font_size=dp(18))
            output_btn.bind(on_press=self.show_output_picker)
            layout.add_widget(output_btn)

            generate_btn = Button(
                text='Generate PDF',
                size_hint_y=0.15,
                font_size=dp(20),
                background_color=(0.2, 0.6, 0.2, 1)
            )
            generate_btn.bind(on_press=self.generate_pdf)
            layout.add_widget(generate_btn)
            self.update_status()
            return layout

        def show_input_picker(self, instance):
            content = BoxLayout(orientation='vertical', spacing=dp(10))
            filechooser = FileChooserListView(filters=['*.md', '*.txt', '*.json'], size_hint_y=0.9)
            btn_layout = BoxLayout(size_hint_y=0.1, spacing=dp(10))
            select_btn = Button(text='Select', font_size=dp(16))
            cancel_btn = Button(text='Cancel', font_size=dp(16))
            popup = Popup(title='Select Input File', content=content, size_hint=(0.9, 0.9))

            def on_select(btn):
                if filechooser.selection:
                    self.input_file = filechooser.selection[0]
                    self.update_status()
                    popup.dismiss()

            select_btn.bind(on_press=on_select)
            cancel_btn.bind(on_press=popup.dismiss)
            btn_layout.add_widget(select_btn)
            btn_layout.add_widget(cancel_btn)
            content.add_widget(filechooser)
            content.add_widget(btn_layout)
            popup.open()

        def show_output_picker(self, instance):
            content = BoxLayout(orientation='vertical', spacing=dp(10))
            filechooser = FileChooserListView(dirselect=True, size_hint_y=0.9)
            btn_layout = BoxLayout(size_hint_y=0.1, spacing=dp(10))
            select_btn = Button(text='Select', font_size=dp(16))
            cancel_btn = Button(text='Cancel', font_size=dp(16))
            popup = Popup(title='Select Output Folder', content=content, size_hint=(0.9, 0.9))

            def on_select(btn):
                self.output_folder = filechooser.path
                self.output_pdf_path = None
                self.update_status()
                popup.dismiss()

            select_btn.bind(on_press=on_select)
            cancel_btn.bind(on_press=popup.dismiss)
            btn_layout.add_widget(select_btn)
            btn_layout.add_widget(cancel_btn)
            content.add_widget(filechooser)
            content.add_widget(btn_layout)
            popup.open()

        def update_status(self):
            input_name = os.path.basename(self.input_file) if self.input_file else "None"
            if self.output_pdf_path:
                output_name = os.path.basename(self.output_pdf_path)
            else:
                output_name = os.path.basename(self.output_folder) if self.output_folder else "None"
            self.status_label.text = f"Input: {input_name}\nOutput: {output_name}"

        def generate_pdf(self, instance):
            if not self.input_file:
                self.show_message("Error", "Please select an input file")
                return
            if not self.output_folder and not self.output_pdf_path:
                self.show_message("Error", "Please select an output folder")
                return

            try:
                if self.output_pdf_path:
                    output_pdf = self.output_pdf_path
                else:
                    output_pdf = os.path.join(
                        self.output_folder,
                        os.path.basename(self.input_file).replace(".", "_") + ".pdf"
                    )
                generate_pdf_from_file(self.input_file, output_pdf)
                self.show_message("Success", f"PDF generated:\n{os.path.basename(output_pdf)}")
            except Exception as e:
                self.show_message("Error", f"Failed to generate PDF:\n{str(e)}")

        def show_message(self, title, message):
            content = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
            label = Label(text=message, font_size=dp(16), size_hint_y=0.8)
            btn = Button(text='OK', size_hint_y=0.2, font_size=dp(18))
            popup = Popup(title=title, content=content, size_hint=(0.8, 0.4))
            btn.bind(on_press=popup.dismiss)
            content.add_widget(label)
            content.add_widget(btn)
            popup.open()

    return PDFGeneratorApp


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Generate a formatted PDF from a markdown, text, or JSON file."
    )
    parser.add_argument("source", nargs="?", help="Input file (.md, .txt, .json)")
    parser.add_argument("--input", dest="input_path", help="Input file (.md, .txt, .json)")
    parser.add_argument("--output", "-o", help="Output PDF path")
    parser.add_argument("--gui", action="store_true", help="Launch the Kivy GUI instead of headless mode")
    args = parser.parse_args(argv)

    input_value = args.input_path or args.source

    if args.gui:
        try:
            app_cls = create_pdf_generator_app(initial_input=input_value, initial_output=args.output)
        except RuntimeError as exc:
            print(f"Error: {exc}")
            return 1
        app_cls().run()
        return 0

    if not input_value:
        parser.error("input is required unless --gui is used")

    try:
        output = generate_pdf_from_file(input_value, args.output)
    except Exception as exc:
        print(f"Error: {exc}")
        return 1

    print(f"PDF generated: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
