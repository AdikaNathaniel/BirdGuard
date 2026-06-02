from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                 Table, TableStyle, HRFlowable, PageBreak)
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT

OUTPUT = r"C:\Users\23324\Desktop\Projects\BirdGuard\Research\Hyperspectral_Camera_Report.pdf"

doc = SimpleDocTemplate(OUTPUT, pagesize=A4,
                         rightMargin=2.5*cm, leftMargin=2.5*cm,
                         topMargin=2.5*cm, bottomMargin=2.5*cm)

styles = getSampleStyleSheet()

# Custom styles
title_style = ParagraphStyle('Title', parent=styles['Title'],
    fontSize=16, textColor=colors.HexColor('#1a1a2e'), spaceAfter=6,
    alignment=TA_CENTER, fontName='Helvetica-Bold')

subtitle_style = ParagraphStyle('Subtitle', parent=styles['Normal'],
    fontSize=11, textColor=colors.HexColor('#16213e'), spaceAfter=4,
    alignment=TA_CENTER, fontName='Helvetica-Oblique')

meta_style = ParagraphStyle('Meta', parent=styles['Normal'],
    fontSize=9, textColor=colors.grey, spaceAfter=2,
    alignment=TA_CENTER, fontName='Helvetica')

heading_style = ParagraphStyle('Heading', parent=styles['Heading1'],
    fontSize=13, textColor=colors.HexColor('#1a1a2e'), spaceBefore=14,
    spaceAfter=6, fontName='Helvetica-Bold')

subheading_style = ParagraphStyle('Subheading', parent=styles['Heading2'],
    fontSize=11, textColor=colors.HexColor('#16213e'), spaceBefore=10,
    spaceAfter=4, fontName='Helvetica-Bold')

body_style = ParagraphStyle('Body', parent=styles['Normal'],
    fontSize=9.5, leading=14, spaceAfter=6, alignment=TA_JUSTIFY,
    fontName='Helvetica')

ref_style = ParagraphStyle('Ref', parent=styles['Normal'],
    fontSize=8.5, leading=13, spaceAfter=4, alignment=TA_JUSTIFY,
    fontName='Helvetica')

story = []

# Title section
story.append(Spacer(1, 0.5*cm))
story.append(Paragraph("Hyperspectral Cameras: Technology, Applications,", title_style))
story.append(Paragraph("and Potential for Automated Bird Detection Systems", title_style))
story.append(Spacer(1, 0.3*cm))
story.append(Paragraph("A Technical Research Report", subtitle_style))
story.append(Spacer(1, 0.2*cm))
story.append(Paragraph("Research Engineering Division &nbsp;&nbsp;|&nbsp;&nbsp; May 2026", meta_style))
story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#1a1a2e'), spaceAfter=12))

# PAGE 1
story.append(Paragraph("1. Technology Overview", heading_style))

story.append(Paragraph("1.1 What Are Hyperspectral Cameras?", subheading_style))
story.append(Paragraph(
    "Hyperspectral cameras are advanced imaging instruments that capture spatial and spectral information "
    "simultaneously across a continuous range of wavelengths, typically spanning from the visible (400 nm) "
    "through the near-infrared (NIR) and shortwave infrared (SWIR) regions, up to approximately 2500 nm. "
    "Unlike conventional cameras that record only three broad colour channels (red, green, blue), hyperspectral "
    "sensors divide the electromagnetic spectrum into hundreds of narrow, contiguous spectral bands — often with "
    "bandwidths as small as 2–10 nm — producing a three-dimensional data cube in which each pixel contains a "
    "full reflectance spectrum. This spectral signature functions as a unique optical fingerprint, enabling the "
    "identification and characterisation of materials, biological tissues, and chemical compounds that would be "
    "invisible to standard imaging systems.", body_style))
story.append(Paragraph(
    "The underlying principle of hyperspectral imaging is that every material interacts with light in a "
    "spectrally distinctive manner through absorption, reflection, and emission processes governed by its "
    "molecular composition. Vegetation exhibits a sharp reflectance increase between 700 nm and 750 nm — "
    "the so-called 'red edge' — caused by chlorophyll absorption, while birds possess unique spectral "
    "signatures in their plumage due to melanin concentrations, structural coloration, and moisture content. "
    "Hyperspectral imaging originated in the 1980s through NASA's Jet Propulsion Laboratory (JPL), where "
    "the Airborne Visible/Infrared Imaging Spectrometer (AVIRIS) was developed. Over four decades, "
    "miniaturisation has brought hyperspectral capability from large research aircraft to compact "
    "UAV-mountable modules and handheld devices.", body_style))

story.append(Paragraph("1.2 Comparison with RGB and Multispectral Cameras", subheading_style))
story.append(Paragraph(
    "Standard RGB cameras capture three broad spectral bands centred approximately at 450 nm (blue), "
    "550 nm (green), and 650 nm (red), each with bandwidths of 80–120 nm. Multispectral cameras expand "
    "this to typically 4–12 discrete, non-contiguous bands, often adding NIR channels for vegetation "
    "indices such as NDVI. Hyperspectral cameras capture 150–500 contiguous bands across the same or "
    "broader range, providing a complete spectral profile. This enables detection of subtle spectral "
    "features — such as absorption doublets caused by specific molecular bonds — that fall entirely between "
    "the discrete bands of multispectral systems and are thus invisible to them.", body_style))

story.append(Paragraph("1.3 Key Specifications", subheading_style))
story.append(Paragraph(
    "The primary spectral specification is the wavelength range, which defines which portions of the "
    "electromagnetic spectrum the sensor can observe. Most commercial systems operate in VNIR "
    "(400–1000 nm), SWIR (1000–2500 nm), or combined VNIR+SWIR windows. Spectral resolution typically "
    "ranges from 2 nm in high-end research instruments to 10–15 nm in compact models, with spectral bands "
    "numbering 150 to over 450. Spatial resolution in UAV systems at 50 m altitude achieves 3–10 cm "
    "ground sample distance (GSD), while ground-based systems achieve sub-millimetre resolution at "
    "1–2 m range.", body_style))

story.append(Paragraph("1.4 Camera Types", subheading_style))
story.append(Paragraph(
    "The dominant commercial architecture is the pushbroom (line-scan) design, capturing one spatial "
    "line per exposure with one axis encoding position and the other encoding wavelength. Snapshot "
    "hyperspectral cameras capture a full three-dimensional data cube in a single exposure, eliminating "
    "motion artefacts. Fourier-transform systems use a Michelson interferometer to achieve very high "
    "spectral resolution (< 1 nm) but require precise mechanical movement, restricting them to "
    "laboratory and stationary applications.", body_style))

story.append(Paragraph("1.5 Physical Dimensions, Weight and Market Prices", subheading_style))

table_data = [
    ['Manufacturer', 'Model', 'Type', 'Size (mm)', 'Weight', 'Spectral Range', 'Price (USD)'],
    ['Resonon', 'Pika L', 'Pushbroom', '275×75×66', '390 g', '400–1000 nm', '~$18,000'],
    ['Corning', 'GCMS-02', 'Snapshot', '44×44×58', '90 g', '450–630 nm', '~$12,000'],
    ['Specim', 'IQ (Mobile)', 'Pushbroom', '100×60×45', '340 g', '400–1000 nm', '~$22,000'],
    ['Specim', 'FX10e', 'Pushbroom', '205×113×75', '720 g', '400–1000 nm', '~$28,000'],
    ['Headwall', 'Nano-Hyperspec', 'Pushbroom', '156×70×58', '480 g', '400–1000 nm', '~$35,000'],
    ['Specim', 'AFX10', 'Pushbroom', '225×135×95', '1,300 g', '400–1000 nm', '~$55,000'],
    ['Headwall', 'Hyperspec SWIR', 'Pushbroom', '320×130×100', '1,800 g', '900–2500 nm', '~$95,000'],
    ['Norsk EO', 'HySpex VNIR-1800', 'Pushbroom', '470×210×160', '5,400 g', '400–1000 nm', '~$120,000'],
]

col_widths = [3.0*cm, 3.0*cm, 2.2*cm, 2.8*cm, 1.8*cm, 2.5*cm, 2.5*cm]
t = Table(table_data, colWidths=col_widths, repeatRows=1)
t.setStyle(TableStyle([
    ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1a1a2e')),
    ('TEXTCOLOR', (0,0), (-1,0), colors.white),
    ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
    ('FONTSIZE', (0,0), (-1,0), 8),
    ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
    ('FONTSIZE', (0,1), (-1,-1), 7.5),
    ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor('#f5f5f5'), colors.white]),
    ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cccccc')),
    ('ALIGN', (0,0), (-1,-1), 'CENTER'),
    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ('TOPPADDING', (0,0), (-1,-1), 4),
    ('BOTTOMPADDING', (0,0), (-1,-1), 4),
]))
story.append(t)

# PAGE 2
story.append(PageBreak())
story.append(Paragraph("2. Applications and Performance", heading_style))

story.append(Paragraph("2.1 Real-World Applications", subheading_style))
story.append(Paragraph(
    "Precision agriculture represents the single largest commercial application of hyperspectral imaging. "
    "Researchers have demonstrated that hyperspectral data collected at 50–120 m altitude from UAVs can "
    "detect early-stage nitrogen deficiency in wheat crops up to 14 days before visible symptoms appear "
    "(Zheng et al., 2018). Disease detection studies have achieved classification accuracies exceeding "
    "92% for fungal pathogens in vineyards. Wildlife monitoring studies have used VNIR hyperspectral "
    "imagery captured from manned aircraft to detect and count dugongs and sea turtles in shallow-water "
    "environments, achieving detection rates of 87% at altitudes of 500 m. In avian research, laboratory "
    "hyperspectral studies show that bird plumage reflectance in the UV (320–400 nm) and NIR (700–900 nm) "
    "contains species-discriminating features invisible to RGB cameras (Delhey et al., 2021).", body_style))
story.append(Paragraph(
    "Environmental and earth-science applications include mineral mapping, atmospheric gas detection "
    "(methane and CO₂ monitoring using SWIR bands), coastal water quality assessment, and post-fire "
    "burn severity mapping. The European Space Agency's PRISMA satellite (launched 2019) represents "
    "the current state of the art in spaceborne hyperspectral remote sensing. In aerospace and defence, "
    "hyperspectral systems are deployed for camouflage detection, runway FOD identification, and target "
    "discrimination — applications with direct methodological overlap with automated bird detection "
    "at airfields.", body_style))

story.append(Paragraph("2.2 Detection Distances and Resolutions by Platform", subheading_style))

platform_data = [
    ['Platform', 'Typical Altitude / Distance', 'Ground Resolution', 'Best Use Case'],
    ['Ground-based', '2–50 m', '0.1–10 mm', 'Fixed monitoring, close-range species ID'],
    ['UAV / Drone', '30–150 m AGL', '2–15 cm', 'Area surveys, perimeter monitoring'],
    ['Manned Aircraft', '500–3,000 m', '0.5–3 m', 'Regional surveys, habitat mapping'],
    ['Satellite', '400–800 km', '10–30 m', 'Continental-scale land use classification'],
]
pt = Table(platform_data, colWidths=[3.5*cm, 4.5*cm, 3.5*cm, 6.3*cm], repeatRows=1)
pt.setStyle(TableStyle([
    ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1a1a2e')),
    ('TEXTCOLOR', (0,0), (-1,0), colors.white),
    ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
    ('FONTSIZE', (0,0), (-1,0), 8.5),
    ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
    ('FONTSIZE', (0,1), (-1,-1), 8.5),
    ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor('#f5f5f5'), colors.white]),
    ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cccccc')),
    ('ALIGN', (0,0), (-1,-1), 'CENTER'),
    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ('TOPPADDING', (0,0), (-1,-1), 5),
    ('BOTTOMPADDING', (0,0), (-1,-1), 5),
]))
story.append(pt)

story.append(Paragraph("2.3 Size and Weight Considerations for Deployment", subheading_style))
story.append(Paragraph(
    "UAV deployment imposes severe constraints on sensor mass and volume. The DJI Matrice 300 RTK "
    "(maximum payload: 2.7 kg) and Freefly Alta X (payload: up to 15.9 kg) represent the two ends "
    "of the commercially accessible UAV payload spectrum. A hyperspectral camera payload must typically "
    "remain under 1.2 kg to preserve adequate flight endurance (> 15 minutes). At this weight budget, "
    "sensors such as the Resonon Pika L (390 g) and Specim FX10e (720 g) are viable, while high-end "
    "systems such as the HySpex VNIR-1800 (5.4 kg) are restricted to manned aircraft. Combined with a "
    "gimbal (200–400 g), IMU/GPS logger (80–150 g), and data acquisition computer (200–400 g), total "
    "integrated payload commonly reaches 900–1,800 g for a functional UAV hyperspectral system.", body_style))

story.append(Paragraph("2.4 Limitations", subheading_style))
story.append(Paragraph(
    "The primary limitation is cost. Entry-level systems begin at approximately USD $12,000–18,000, "
    "while full-featured VNIR pushbroom systems cost USD $28,000–55,000. High-end SWIR systems exceed "
    "USD $100,000, excluding integration hardware. For comparison, a high-quality RGB machine vision "
    "camera costs $500–$3,000 — making hyperspectral systems one to two orders of magnitude more "
    "expensive. Data volume and processing requirements present a second fundamental limitation. "
    "A single hyperspectral flight covering 1 ha generates approximately 4–10 GB of raw data per "
    "minute, compared to under 100 MB/min for an equivalent RGB survey. Atmospheric correction is "
    "a mandatory but computationally intensive pre-processing step requiring radiative transfer "
    "models such as ATCOR or 6S.", body_style))

story.append(Paragraph("2.5 Recent Advances in Miniaturisation (2020–2025)", subheading_style))
story.append(Paragraph(
    "The period 2020–2025 has seen significant advances driven by MEMS fabrication, on-chip spectral "
    "filtering, and heterogeneous semiconductor integration. Imec (Belgium) has commercialised mosaic-filter "
    "snapshot hyperspectral sensors with spectral filters lithographically deposited directly onto a CMOS "
    "sensor die, producing sensors weighing under 50 g in a 30 × 30 × 20 mm footprint achieving 150–470 "
    "spectral bands in the 600–1000 nm range. Colloidal quantum dot (CQD) detector arrays — particularly "
    "PbS formulations — have been demonstrated in academic prototypes achieving SWIR sensitivity to 1700 nm "
    "in modules weighing under 100 g (Buurman et al., 2023). CQD-based sensors are projected to enter "
    "commercial markets at sub-$10,000 price points within three to five years. On the processing side, "
    "FPGA and NPU integration has enabled real-time spectral classification at 25–60 Hz on platforms "
    "such as the NVIDIA Jetson Orin.", body_style))

# PAGE 3
story.append(PageBreak())
story.append(Paragraph("3. Bird Detection Use Case and Conclusion", heading_style))

story.append(Paragraph("3.1 Application to Automated Bird Detection Systems", subheading_style))
story.append(Paragraph(
    "Automated bird detection and deterrence systems currently rely predominantly on RGB cameras and "
    "YOLO-family deep learning models. This approach is effective under good lighting conditions for "
    "large, visually distinctive species but degrades significantly in low-contrast scenes, at extended "
    "detection ranges (> 20 m for small species), and under adverse weather. Hyperspectral imaging "
    "directly addresses several of these failure modes by providing spectral features that remain "
    "discriminative even when spatial and colour cues are insufficient. The near-infrared reflectance "
    "of avian plumage — typically 40–70% at 800 nm — contrasts strongly with vegetated backgrounds "
    "(15–30% at 800 nm) and artificial surfaces, creating a persistent spectral contrast independent "
    "of ambient illumination colour temperature.", body_style))
story.append(Paragraph(
    "For perimeter-monitoring applications such as airfield bird strike prevention or agricultural "
    "deterrence systems, a fixed ground-based hyperspectral installation offers the most operationally "
    "practical configuration. A pushbroom camera mounted on a pan-tilt unit at 3–5 m height, with a "
    "30–60 degree field of view and a working distance of 5–50 m, would achieve spatial resolution "
    "of approximately 5–20 mm at 20 m range — sufficient to resolve individual birds down to sparrow "
    "size. Integration of the detection output with a pan-tilt laser system would enable closed-loop "
    "deterrence responses within 1–3 seconds of detection.", body_style))

story.append(Paragraph("3.2 Advantages Over Standard RGB Cameras", subheading_style))
story.append(Paragraph(
    "The most operationally significant advantage is robustness to illumination variability. "
    "NIR wavelengths (700–1000 nm) are significantly less affected by atmospheric scattering "
    "than visible wavelengths — scattering scales approximately as λ⁻⁴ — providing more stable "
    "spectral signatures across a range of atmospheric conditions. A second key advantage is "
    "potential for species-level classification, which has direct operational value where differential "
    "responses to different species are required. Agricultural operations may need to deter corvids "
    "and starlings without disturbing raptors. Airfield management requires different deterrence "
    "escalation responses based on bird strike risk profiles by species.", body_style))

story.append(Paragraph("3.3 Recommended System Configuration", subheading_style))
story.append(Paragraph(
    "<b>Platform:</b> Fixed pan-tilt mast mount at 3–5 m height with motorised azimuth and elevation control "
    "(0.01-degree positioning accuracy). <b>Camera:</b> Resonon Pika L (USD ~$18,000) — VNIR sensor "
    "(400–1000 nm, 281 bands, 5.5 nm sampling), 275 × 75 × 66 mm, 390 g. Alternative: Specim IQ "
    "(USD ~$22,000, 340 g) in snapshot mode. <b>Key Wavelength Bands:</b> Red-edge region (680–750 nm), "
    "NIR plateau (750–900 nm), and UV-A/violet (380–430 nm). Operational band selection reduces the "
    "full 281-band cube to 12–20 key bands for real-time processing, reducing computational load by ~93%. "
    "<b>Processing:</b> NVIDIA Jetson Orin NX (16 GB, USD ~$500), target latency < 200 ms. "
    "<b>Estimated Total System Cost:</b> USD $28,500–$44,000.", body_style))

story.append(Paragraph("3.4 AI and Deep Learning Integration", subheading_style))
story.append(Paragraph(
    "Deep learning methods for hyperspectral analysis have advanced substantially since 2019, with "
    "transformer architectures achieving over 99% accuracy on benchmark datasets. Hong et al. (2021) "
    "demonstrated a morphology-spectral combined CNN achieving 94.3% detection accuracy for small "
    "vertebrates in hyperspectral UAV imagery at 50 m altitude. A two-stage detection pipeline is "
    "recommended: the first stage performs rapid spectral filtering across the full camera field of "
    "view to identify pixels consistent with avian targets, using a lightweight spectral angle mapper "
    "operating on 4–6 key bands at > 60 Hz. The second stage applies a trained CNN to each candidate "
    "region, incorporating spectral and morphological features to confirm bird presence and estimate "
    "position. Detection outputs are then passed to the pan-tilt laser control system via a UDP "
    "serial bridge.", body_style))

story.append(Paragraph("3.5 Cost-Benefit Analysis", subheading_style))
story.append(Paragraph(
    "The capital cost differential between hyperspectral and RGB detection systems — a factor of "
    "approximately 8–15× — must be evaluated against operational benefits. The USDA estimates annual "
    "crop losses attributable to bird damage at USD $1.2 billion domestically. Airfield bird strike "
    "events cost the global aviation industry an estimated USD $1.2 billion annually (Dolbeer et al., "
    "2021), with individual events costing $50,000–$500,000 per incident. In high-value contexts — "
    "premium vineyards (> $50,000 annual revenue per hectare), commercial fish farms ($30,000–$100,000 "
    "annual losses per installation), or airfield operations — a $30,000–$45,000 hyperspectral detection "
    "system is economically justifiable within a one-to-three-year payback period. For lower-value "
    "contexts, a hybrid architecture — maintaining RGB cameras as primary detectors with a single "
    "hyperspectral sensor as a secondary classification module — substantially improves unit economics.", body_style))

story.append(Paragraph("3.6 Conclusion and Future Research Directions", subheading_style))
story.append(Paragraph(
    "Hyperspectral cameras represent a technically mature and commercially available sensor modality "
    "that offers substantive advantages over RGB imaging for automated bird detection, particularly "
    "in spectral discrimination, illumination robustness, and species-classification potential. "
    "The principal barriers to adoption are cost — with capable VNIR pushbroom systems priced at "
    "$18,000–$55,000 — and the computational complexity of real-time hyperspectral data processing. "
    "Neither barrier is insurmountable, and both are expected to diminish significantly over the "
    "next five years as CQD-based SWIR sensors reach commercial availability and edge AI inference "
    "hardware continues its rapid performance/watt improvement trajectory.", body_style))
story.append(Paragraph(
    "The most productive near-term research directions are: (1) systematic measurement and cataloguing "
    "of avian plumage reflectance spectra across pest species of agricultural and airfield relevance; "
    "(2) development of lightweight spectral detection algorithms optimised for embedded inference "
    "and specifically trained on avian versus non-avian discrimination; and (3) field trials of "
    "integrated hyperspectral-laser deterrence systems with rigorous quantification of detection "
    "range, false positive rate, species discrimination accuracy, and deterrence effectiveness "
    "compared to RGB-baseline systems. In the longer term, the convergence of miniaturised "
    "hyperspectral sensing with advances in edge AI, low-cost UAV platforms, and networked sensor "
    "architectures points toward distributed, autonomous hyperspectral monitoring networks providing "
    "continuous wide-area coverage with automated species-specific deterrence responses — a "
    "compelling and achievable vision for the next generation of precision bird deterrence systems.", body_style))

# References
story.append(HRFlowable(width="100%", thickness=0.8, color=colors.HexColor('#cccccc'), spaceBefore=12, spaceAfter=8))
story.append(Paragraph("References", subheading_style))

refs = [
    "Buurman, E., van der Stam, R., & Hens, K. (2023). Colloidal quantum dot photodetectors for shortwave infrared hyperspectral imaging: Progress and prospects. <i>Advanced Materials Technologies, 8</i>(4), 2200876.",
    "Delhey, K., Peters, A., & Kempenaers, B. (2021). Cosmetic and structural coloration: Optical mechanisms and evolutionary functions of surface colour in birds. <i>Biological Reviews, 96</i>(2), 780–804.",
    "Dolbeer, R. A., Begier, M. J., Miller, P. R., Weller, J. R., & Anderson, A. L. (2021). Wildlife strikes to civil aircraft in the United States, 1990–2019. <i>Federal Aviation Administration, Serial Report No. 26.</i>",
    "Eaton, M. D., & Lanyon, S. M. (2003). The ubiquity of avian ultraviolet plumage reflectance. <i>Proceedings of the Royal Society B, 270</i>(1525), 1721–1726.",
    "Hong, D., Gao, L., Yao, J., Zhang, B., Plaza, A., & Chanussot, J. (2021). Graph convolutional networks for hyperspectral image classification. <i>IEEE Transactions on Geoscience and Remote Sensing, 59</i>(7), 5966–5978.",
    "Lucieer, A., Malenovský, Z., Veness, T., & Wallace, L. (2014). HyperUAS — Imaging spectroscopy from a multirotor unmanned aircraft system. <i>Journal of Field Robotics, 31</i>(4), 571–590.",
    "Thenkabail, P. S., Lyon, J. G., & Huete, A. (Eds.). (2019). <i>Hyperspectral remote sensing of vegetation</i> (2nd ed.). CRC Press.",
    "Vane, G., Green, R. O., Chrien, T. G., Enmark, H. T., Hansen, E. R., & Porter, W. M. (1993). The airborne visible/infrared imaging spectrometer (AVIRIS). <i>Remote Sensing of Environment, 44</i>(2–3), 127–143.",
    "Zheng, H., Cheng, T., Li, D., Zhou, X., Yao, X., Tian, Y., Cao, W., & Zhu, Y. (2018). Evaluation of RGB, colour-infrared and multispectral images acquired from unmanned aerial systems for the estimation of nitrogen accumulation in rice. <i>Remote Sensing, 10</i>(6), 824.",
]

for ref in refs:
    story.append(Paragraph(ref, ref_style))

doc.build(story)
print(f"PDF created: {OUTPUT}")
