"""
Generate sample pharmaceutical complaint PDF and EML files for demo.
Run this script once: python generate_sample_data.py
Requires: reportlab (pip install reportlab)
"""
import os
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))


def generate_pdf():
    """Create a realistic FDF complaint PDF using reportlab."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.enums import TA_LEFT, TA_CENTER
    except ImportError:
        print("reportlab not installed. Run: pip install reportlab")
        return

    path = os.path.join(OUTPUT_DIR, "complaint_amoxicillin.pdf")
    doc = SimpleDocTemplate(path, pagesize=A4,
                             leftMargin=25*mm, rightMargin=25*mm,
                             topMargin=20*mm, bottomMargin=20*mm)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('title', parent=styles['Heading1'], fontSize=14, spaceAfter=4)
    sub_style = ParagraphStyle('sub', parent=styles['Normal'], fontSize=9, textColor=colors.grey)
    normal = styles['Normal']
    normal.fontSize = 10
    normal.leading = 14

    header_style = ParagraphStyle('header', parent=styles['Heading2'], fontSize=11,
                                   textColor=colors.HexColor('#1D4ED8'), spaceBefore=12, spaceAfter=6)

    content = []

    # Header
    content.append(Paragraph("APOLLO PHARMACY PVT. LTD.", title_style))
    content.append(Paragraph("Customer Quality Complaint Form", sub_style))
    content.append(Paragraph("Complaint Reference: AP-CC-2024-0892", sub_style))
    content.append(Spacer(1, 10*mm))

    # Complaint Details Table
    data = [
        ['Field', 'Details'],
        ['Date of Complaint', '15 October 2024'],
        ['Reported By', 'Mr. Rajesh Sharma, QA Head'],
        ['Customer Organization', 'Apollo Pharmacy Pvt. Ltd., Mumbai'],
        ['Contact', 'rajesh.sharma@apollopharmacy.in | +91-22-6789-0123'],
        ['Supplier / Manufacturer', 'PharmaGen India Ltd., Hyderabad'],
        ['Product Name', 'Amoxicillin Capsules IP'],
        ['Product Strength', '500 mg'],
        ['Batch Number', 'BMX24601'],
        ['Manufacturing Date', 'January 2024'],
        ['Expiry Date', 'December 2025'],
        ['Quantity Received', '5,000 capsules (250 bottles × 20 capsules)'],
        ['Quantity Affected', '200 bottles (approximately 4,000 capsules)'],
        ['Complaint Category', 'Quality – Discoloration'],
    ]

    table = Table(data, colWidths=[65*mm, 105*mm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1D4ED8')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BACKGROUND', (0, 1), (0, -1), colors.HexColor('#EFF6FF')),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    content.append(table)

    # Complaint Description
    content.append(Paragraph("Complaint Description", header_style))
    content.append(Paragraph(
        "During routine quality check at our central warehouse (Mumbai), our QA team observed "
        "significant discoloration in approximately 80% of the received Amoxicillin Capsule 500 mg "
        "(Batch BMX24601). The capsule shells, which should be light pink in color (as per the "
        "approved artwork), were found to be brownish-yellow, indicating potential degradation. "
        "The product was stored under recommended conditions (15-25°C, &lt;65% RH) throughout "
        "the supply chain. No physical damage to the blister packaging was observed. "
        "Customer complaints have been received from 3 retail outlets regarding the appearance "
        "of the product.", normal))

    content.append(Paragraph("Immediate Actions Taken", header_style))
    content.append(Paragraph(
        "1. The entire batch BMX24601 has been placed under quarantine at our warehouse.<br/>"
        "2. Sales of this batch have been suspended with immediate effect.<br/>"
        "3. Retain samples have been kept for further investigation.<br/>"
        "4. Customers who purchased this batch have been informed to return the product.",
        normal))

    content.append(Paragraph("Requested Actions from Manufacturer", header_style))
    content.append(Paragraph(
        "We request PharmaGen India Ltd. to:<br/>"
        "1. Conduct a thorough investigation of Batch BMX24601.<br/>"
        "2. Provide a root cause analysis report within 15 working days.<br/>"
        "3. Issue replacement stock for the affected quantity (200 bottles).<br/>"
        "4. Confirm whether other batches are affected and initiate CAPA.",
        normal))

    content.append(Spacer(1, 10*mm))
    content.append(Paragraph(
        f"Signature: Rajesh Sharma &nbsp;&nbsp;&nbsp; Date: 15 October 2024 &nbsp;&nbsp;&nbsp; "
        f"Designation: Quality Assurance Head", sub_style))

    doc.build(content)
    print(f"Generated: {path}")


def generate_eml():
    """Create a realistic API complaint email (.eml file)."""
    msg = MIMEMultipart('alternative')
    msg['Subject'] = "Quality Complaint – Metformin Hydrochloride API Batch MFH260712A – Particle Contamination"
    msg['From'] = "Dr. Klaus Weber <k.weber@scigen-pharma.de>"
    msg['To'] = "complaints@pharmagen.in"
    msg['Date'] = "Mon, 14 Oct 2024 09:32:15 +0100"
    msg['X-Priority'] = "1"

    body = """Dear Complaints Team,

We are writing to formally raise a quality complaint regarding a recent delivery of Metformin Hydrochloride API.

COMPLAINT DETAILS
=================
Customer:         SciGen Pharma GmbH, Frankfurt, Germany
Product:          Metformin Hydrochloride API
Grade / Standard: IP/BP (compliant with Indian Pharmacopoeia and British Pharmacopoeia)
Supplier:         PharmaGen India Ltd.
Batch / Lot No.:  MFH260712A
Manufacturing Date: July 2024
Certificate of Analysis Date: 10 July 2024
Quantity Received: 50 kg (2 HDPE drums, 25 kg each)
Date of Receipt: 22 September 2024

NATURE OF COMPLAINT
===================
During our incoming quality control testing on 14 October 2024, our laboratory 
identified visible particulate contamination in the Metformin Hydrochloride API 
from the above batch. Specifically:

1. Black/dark-coloured particles were observed during dissolution testing
2. Particle size estimated at 0.5–2 mm range (visible to naked eye)
3. Contamination was found in samples from both HDPE drums
4. The Certificate of Analysis supplied does not report any particulate matter

This issue was confirmed by two independent QC analysts and documented with 
photographic evidence (attached separately).

REGULATORY CONCERN
==================
Given that Metformin Hydrochloride is used in the manufacture of finished dosage 
forms for diabetic patients, this contamination represents a potential Critical 
quality failure. We may be required to notify the German Federal Institute for 
Drugs and Medical Devices (BfArM) if this issue is not resolved promptly.

REQUESTED ACTIONS
=================
1. Immediate hold on any remaining material from Batch MFH260712A
2. Root cause analysis and CAPA report within 10 working days
3. Replacement of the affected 50 kg (2 HDPE drums) at no additional cost
4. Confirmation that other batches of Metformin HCl API are not affected

Please acknowledge receipt of this complaint within 24 hours.

Regards,
Dr. Klaus Weber
Head of Quality Control
SciGen Pharma GmbH
Industriepark Höchst, Building G830
65926 Frankfurt am Main, Germany
Tel: +49 69 305 22815
Email: k.weber@scigen-pharma.de
"""

    msg.attach(MIMEText(body, 'plain'))

    path = os.path.join(OUTPUT_DIR, "complaint_metformin_email.eml")
    with open(path, 'w', encoding='utf-8') as f:
        f.write(msg.as_string())
    print(f"Generated: {path}")


if __name__ == "__main__":
    generate_pdf()
    generate_eml()
    print("Sample data generation complete!")
