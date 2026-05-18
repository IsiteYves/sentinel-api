import io
from datetime import datetime, timezone
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

_NAVY = colors.HexColor("#1B3A6B")
_RED = colors.HexColor("#E63946")
_LIGHT_GREY = colors.HexColor("#F8F9FA")
_MID_GREY = colors.HexColor("#6C757D")

_CHAIN_OF_CUSTODY = (
    "This report was generated automatically by Sentinel, an independent digital "
    "evidence preservation system. The SHA-256 cryptographic hash was computed "
    "at the precise moment of evidence capture and submitted immediately to the "
    "Bitcoin blockchain via OpenTimestamps for immutable, independently verifiable "
    "timestamping. No human operator had access to alter the content between "
    "capture and hashing. This report constitutes prima facie evidence of the "
    "existence and integrity of the captured digital content as provided under the "
    "Computer Misuse and Cybercrimes Act (CMCA) 2018, Chapter 79A of the Laws of "
    "Kenya, and is formatted for submission to the Kenya Police Service, Office of "
    "the Director of Public Prosecutions (ODPP), and the Judiciary."
)


def _styles() -> dict:
    base = getSampleStyleSheet()
    return {
        "h1": ParagraphStyle(
            "h1",
            fontName="Helvetica-Bold",
            fontSize=18,
            textColor=_NAVY,
            alignment=TA_CENTER,
            spaceAfter=2 * mm,
        ),
        "sub": ParagraphStyle(
            "sub",
            fontName="Helvetica",
            fontSize=9,
            textColor=_MID_GREY,
            alignment=TA_CENTER,
            spaceAfter=6 * mm,
        ),
        "section": ParagraphStyle(
            "section",
            fontName="Helvetica-Bold",
            fontSize=10,
            textColor=_NAVY,
            spaceAfter=3 * mm,
            spaceBefore=6 * mm,
        ),
        "body": ParagraphStyle(
            "body",
            fontName="Helvetica",
            fontSize=9,
            textColor=colors.black,
            leading=14,
            spaceAfter=2 * mm,
        ),
        "mono": ParagraphStyle(
            "mono",
            fontName="Courier",
            fontSize=8,
            textColor=colors.black,
            leading=12,
            backColor=_LIGHT_GREY,
            spaceAfter=2 * mm,
        ),
        "label": ParagraphStyle(
            "label",
            fontName="Helvetica-Bold",
            fontSize=8,
            textColor=_MID_GREY,
        ),
        "value": ParagraphStyle(
            "value",
            fontName="Helvetica",
            fontSize=9,
            textColor=colors.black,
        ),
        "legal": ParagraphStyle(
            "legal",
            fontName="Helvetica",
            fontSize=8,
            textColor=_MID_GREY,
            leading=13,
        ),
        "warning": ParagraphStyle(
            "warning",
            fontName="Helvetica-Bold",
            fontSize=10,
            textColor=_RED,
            alignment=TA_CENTER,
        ),
        "safe": ParagraphStyle(
            "safe",
            fontName="Helvetica-Bold",
            fontSize=10,
            textColor=colors.HexColor("#2D6A4F"),
            alignment=TA_CENTER,
        ),
    }


def _kv_table(rows: list[tuple[str, str]], s: dict) -> Table:
    data = [[Paragraph(k, s["label"]), Paragraph(v, s["value"])] for k, v in rows]
    tbl = Table(data, colWidths=[45 * mm, None], hAlign="LEFT")
    tbl.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return tbl


def generate_report_pdf(case: dict) -> bytes:
    """Render a court-ready PDF for the given case row and return raw bytes."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )
    s = _styles()
    story = []

    # ── Header ────────────────────────────────────────────────────────────────
    story.append(Paragraph("SENTINEL", s["h1"]))
    story.append(
        Paragraph("FORENSIC DIGITAL EVIDENCE REPORT", s["sub"])
    )
    story.append(
        HRFlowable(width="100%", thickness=2, color=_NAVY, spaceAfter=4 * mm)
    )

    # ── Case banner ───────────────────────────────────────────────────────────
    banner_data = [
        [
            Paragraph("CASE REFERENCE", s["label"]),
            Paragraph("CLASSIFICATION"),
        ],
        [
            Paragraph(case["case_id"], s["h1"]),
            Paragraph("FORENSIC EVIDENCE", s["label"]),
        ],
    ]
    banner = Table(banner_data, colWidths=["60%", "40%"])
    banner.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), _LIGHT_GREY),
                ("BOX", (0, 0), (-1, -1), 1, _NAVY),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.white),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(banner)

    # ── Evidence capture details ───────────────────────────────────────────────
    story.append(Paragraph("1. EVIDENCE CAPTURE DETAILS", s["section"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=_NAVY, spaceAfter=3 * mm))

    captured_at_str = case.get("captured_at", "")
    try:
        dt = datetime.fromisoformat(captured_at_str.replace("Z", "+00:00"))
        captured_display = dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    except Exception:
        captured_display = captured_at_str

    detail_rows: list[tuple[str, str]] = [
        ("Captured At:", captured_display),
    ]
    if case.get("source_url"):
        detail_rows.append(("Source URL:", case["source_url"]))
    if case.get("filename"):
        detail_rows.append(("File Name:", case["filename"]))
    detail_rows.append(
        ("Evidence Type:", "URL Capture" if case.get("source_url") else "File Upload")
    )
    story.append(_kv_table(detail_rows, s))

    # ── SHA-256 hash ──────────────────────────────────────────────────────────
    story.append(Paragraph("2. CRYPTOGRAPHIC INTEGRITY (SHA-256)", s["section"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=_NAVY, spaceAfter=3 * mm))
    story.append(Paragraph(case["sha256_hash"], s["mono"]))
    story.append(
        Paragraph(
            "The SHA-256 hash above uniquely identifies the captured content. "
            "Any alteration — even a single byte — produces an entirely different hash, "
            "making tampering immediately detectable.",
            s["body"],
        )
    )

    # ── Blockchain timestamp ──────────────────────────────────────────────────
    story.append(Paragraph("3. BLOCKCHAIN TIMESTAMP", s["section"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=_NAVY, spaceAfter=3 * mm))
    ots_status = case.get("ots_status", "unknown")
    ots_display = {
        "pending_bitcoin_confirmation": "Submitted — Awaiting Bitcoin Block Confirmation",
        "timestamp_unavailable": "Timestamp Submission Failed",
    }.get(ots_status, ots_status)

    story.append(
        _kv_table(
            [
                ("Status:", ots_display),
                ("Network:", "Bitcoin (via OpenTimestamps)"),
                ("Submitted At:", captured_display),
            ],
            s,
        )
    )
    story.append(
        Paragraph(
            "OpenTimestamps anchors the hash to the Bitcoin blockchain, providing a "
            "cryptographically provable timestamp that is tamper-resistant and "
            "independently verifiable by any third party.",
            s["body"],
        )
    )

    # ── Deepfake analysis ─────────────────────────────────────────────────────
    story.append(Paragraph("4. DEEPFAKE / MANIPULATION ANALYSIS", s["section"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=_NAVY, spaceAfter=3 * mm))

    df_status = case.get("df_status")
    if df_status == "analyzed":
        is_df = case.get("df_is_deepfake")
        conf = case.get("df_confidence")
        verdict = "DEEPFAKE DETECTED" if is_df else "No Manipulation Detected"
        verdict_style = s["warning"] if is_df else s["safe"]
        story.append(Paragraph(verdict, verdict_style))
        story.append(Spacer(1, 3 * mm))
        df_rows = [("Analysis Engine:", "Hive AI Visual Deepfake Classifier")]
        if conf is not None:
            df_rows.append(("Confidence Score:", f"{conf}%"))
        story.append(_kv_table(df_rows, s))
    elif df_status == "skipped":
        reason = case.get("df_reason", "N/A")
        story.append(Paragraph(f"Analysis not performed: {reason}", s["body"]))
    else:
        story.append(Paragraph("Analysis not available.", s["body"]))

    # ── Chain of custody ──────────────────────────────────────────────────────
    story.append(Paragraph("5. CHAIN OF CUSTODY STATEMENT", s["section"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=_NAVY, spaceAfter=3 * mm))
    story.append(Paragraph(_CHAIN_OF_CUSTODY, s["legal"]))

    # ── Certification footer ──────────────────────────────────────────────────
    story.append(Spacer(1, 8 * mm))
    story.append(HRFlowable(width="100%", thickness=1, color=_NAVY, spaceAfter=4 * mm))

    report_generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    cert_data = [
        [
            Paragraph("Report Generated By", s["label"]),
            Paragraph("Sentinel Evidence Preservation System v1.0", s["value"]),
        ],
        [
            Paragraph("Report Generated At", s["label"]),
            Paragraph(report_generated, s["value"]),
        ],
        [
            Paragraph("Verification ID", s["label"]),
            Paragraph(case["case_id"], s["value"]),
        ],
        [
            Paragraph("Legal Framework", s["label"]),
            Paragraph(
                "Computer Misuse and Cybercrimes Act (CMCA) 2018, Chapter 79A — Laws of Kenya",
                s["value"],
            ),
        ],
    ]
    cert_tbl = Table(cert_data, colWidths=[45 * mm, None], hAlign="LEFT")
    cert_tbl.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BACKGROUND", (0, 0), (-1, -1), _LIGHT_GREY),
                ("BOX", (0, 0), (-1, -1), 0.5, _NAVY),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(cert_tbl)

    doc.build(story)
    return buf.getvalue()
