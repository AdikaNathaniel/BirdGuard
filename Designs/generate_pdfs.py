from fpdf import FPDF
from fpdf.enums import XPos, YPos
import os

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
IMG1 = os.path.join(OUTPUT_DIR, "BirdGuard-Design-1.jpg")
IMG2 = os.path.join(OUTPUT_DIR, "BirdGurad-Design-2.jpeg")


class BirdGuardPDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 20)
        self.set_text_color(30, 30, 30)
        self.cell(0, 14, "BirdGuard - Design Analysis", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
        self.ln(2)
        self.set_draw_color(180, 180, 180)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(6)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")

    def design_heading(self, title):
        self.set_font("Helvetica", "B", 15)
        self.set_fill_color(40, 40, 40)
        self.set_text_color(255, 255, 255)
        self.cell(0, 11, f"  {title}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True)
        self.ln(4)

    def insert_image(self, path, caption):
        # Centre image, max width 140mm
        img_w = 140
        x = (210 - img_w) / 2
        self.image(path, x=x, w=img_w)
        self.ln(2)
        self.set_font("Helvetica", "I", 9)
        self.set_text_color(100, 100, 100)
        self.cell(0, 6, caption, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
        self.ln(5)

    def section(self, label, color_rgb, items):
        r, g, b = color_rgb
        self.set_font("Helvetica", "B", 12)
        self.set_fill_color(r, g, b)
        self.set_text_color(255, 255, 255)
        self.cell(0, 9, f"  {label}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True)
        self.ln(3)
        self.set_text_color(30, 30, 30)
        self.set_font("Helvetica", "", 11)
        for item in items:
            self.set_x(14)
            self.cell(6, 7, "-", new_x=XPos.RIGHT, new_y=YPos.TOP)
            self.multi_cell(0, 7, item)
            self.ln(1)
        self.ln(5)


# ── Content ───────────────────────────────────────────────────────────────────

d1_pros = [
    "Aluminum extrusion frame provides a rigid, modular structure that is easy to modify or expand.",
    "Dual solar panels positioned on both sides give balanced power generation across different sun angles.",
    "Laser and pan-tilt mechanism are centrally mounted, keeping the centre of gravity low and stable.",
    "Raspberry Pi 4 is enclosed within the frame, protecting it from weather while remaining accessible.",
    "Open-frame design allows good airflow around electronics, reducing thermal throttling risk.",
    "Camera is forward-facing and clearly separated from the laser, reducing lens flare interference.",
    "Compact footprint on the mounting pole suits rooftop or post installation in tight spaces.",
]

d1_cons = [
    "Aluminum extrusion frame adds weight compared to a 3D-printed or sheet-metal alternative.",
    "Two solar panels increase material cost and complexity of the wiring harness.",
    "The exposed wiring visible in the render is a maintenance and reliability concern outdoors.",
    "Pan-tilt servo mounting appears cramped inside the frame, potentially limiting range of motion.",
    "No visible battery housing -- energy storage placement is unclear from this design.",
    "Single camera angle may create blind spots for birds approaching from the sides or rear.",
]

d2_pros = [
    "Fence-post mounting is practical and widely available in farm environments with no extra infrastructure needed.",
    "Dual solar panels on a cross-bracket spread power generation and keep the unit self-sufficient off-grid.",
    "Weatherproof camera housing looks robust and suitable for outdoor all-season operation.",
    "BirdGuard branding on the unit presents a polished, product-ready aesthetic.",
    "Compact, self-contained unit on a single post is easy to reposition across a field.",
    "Clean cable management visible along the post reduces snagging and wear on wiring.",
]

d2_cons = [
    "Fence-post mount may not provide enough height for wide-area laser coverage in tall-crop fields.",
    "Solar panel cross-bracket may act as a wind sail, risking unit instability in high-wind rural areas.",
    "Single camera lens shown may not have wide enough field of view for full perimeter detection.",
    "Post mounting limits aiming flexibility -- a fixed post cannot track birds moving outside the laser arc.",
    "No visible weatherproof seal or IP rating indicator, making environmental protection unclear.",
    "Cable running down the post is exposed and could be damaged by animals or farm machinery.",
]

# ── Build single PDF ──────────────────────────────────────────────────────────

pdf = BirdGuardPDF()

# Page 1 - Design 1
pdf.add_page()
pdf.design_heading("Design 1")
pdf.insert_image(IMG1, "Figure 1: Labeled CAD render showing internal components and structure")
pdf.section("Pros", (34, 139, 34), d1_pros)
pdf.section("Cons", (180, 50, 50), d1_cons)

# Page 2 - Design 2
pdf.add_page()
pdf.design_heading("Design 2")
pdf.insert_image(IMG2, "Figure 2: Photorealistic render showing field deployment on a farm fence post")
pdf.section("Pros", (34, 139, 34), d2_pros)
pdf.section("Cons", (180, 50, 50), d2_cons)

out = os.path.join(OUTPUT_DIR, "BirdGuard-Design-Analysis.pdf")
pdf.output(out)
print(f"Saved: {out}")
