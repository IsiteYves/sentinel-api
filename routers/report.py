from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from models import ReportRequest
from services.pdf_gen import generate_report_pdf
from services.storage import get_case

router = APIRouter(prefix="/report", tags=["report"])


@router.post("/generate")
async def generate_report(req: ReportRequest):
    """
    Generate a court-ready PDF Sentinel Report for the given case_id.
    Returns a PDF binary with appropriate headers.
    """
    row = await get_case(req.case_id)
    if not row:
        raise HTTPException(status_code=404, detail="Case not found")

    pdf_bytes = generate_report_pdf(row)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="Sentinel-Report-{req.case_id}.pdf"',
            "Content-Length": str(len(pdf_bytes)),
        },
    )
