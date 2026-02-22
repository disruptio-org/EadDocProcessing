"""Async worker tasks — full processing flow orchestration."""

from __future__ import annotations

import uuid

import structlog

from app.reconcile.engine import reconcile
from app.schemas.common import (
    DocumentRecord,
    FinalStatus,
    JobStatus,
    PageText,
)
from app.services.boundary_detection import detect_boundaries
from app.services.excel_export import generate_index_excel
from app.services.pdf_splitter import split_pdf
from app.services.pipeline_a import run_pipeline_a
from app.services.pipeline_b import run_pipeline_b
from app.services.text_extraction import extract_text_by_page
from app.storage import local as storage
from app.storage.job_store import update_job

logger = structlog.get_logger(__name__)


def process_full_flow(
    job_id: str,
    source_file_id: str,
    mode: str = "dual",
) -> None:
    """Execute the full processing pipeline for a batch PDF.

    Steps:
    1. Extract text from all pages
    2. Detect document boundaries (page ranges)
    3. Run Pipeline A on each document
    4. Run Pipeline B on each document
    5. Reconcile A vs B results
    6. Split the PDF into individual documents
    7. Generate index Excel file
    8. Create reject records for MISMATCH/NEEDS_REVIEW

    This function is designed to be called from an RQ worker or a thread.
    """
    log = logger.bind(job_id=job_id, source_file_id=source_file_id)

    try:
        update_job(job_id, status=JobStatus.RUNNING, progress=0.0, current_step="Starting")
        log.info("process_started", mode=mode)

        # Step 1: Extract text
        update_job(job_id, progress=0.05, current_step="Extracting text")
        pdf_path = str(storage.get_upload_path(source_file_id))
        pages_text = extract_text_by_page(pdf_path)
        storage.save_artifact(source_file_id, "text_extraction", [p.model_dump() for p in pages_text])
        log.info("text_extracted", pages=len(pages_text))

        # Step 2: Detect boundaries
        update_job(job_id, progress=0.10, current_step="Detecting boundaries")
        ranges = detect_boundaries(pages_text)
        storage.save_artifact(source_file_id, "boundaries", [r.model_dump() for r in ranges])
        log.info("boundaries_detected", documents=len(ranges))

        # Step 3: Split PDF
        update_job(job_id, progress=0.15, current_step="Splitting PDF")
        split_docs = split_pdf(pdf_path, ranges, source_file_id)
        doc_id_mapping = {}
        for sd in split_docs:
            doc_id_mapping[(sd.page_range.start_page, sd.page_range.end_page)] = sd.doc_id
        log.info("pdf_split", documents=len(split_docs))

        # Step 4 & 5: Run pipelines on each document
        all_records: list[DocumentRecord] = []
        total_docs = len(ranges)
        progress_per_doc = 0.60 / max(total_docs, 1)  # 60% for extraction + reconcile

        for i, page_range in enumerate(ranges):
            doc_key = (page_range.start_page, page_range.end_page)
            doc_id = doc_id_mapping.get(doc_key, str(uuid.uuid4()))
            doc_pages = [p for p in pages_text if page_range.start_page <= p.page <= page_range.end_page]

            progress = 0.20 + (i * progress_per_doc)
            update_job(
                job_id,
                progress=round(progress, 2),
                current_step=f"Processing doc {i + 1}/{total_docs} (pages {page_range.start_page}-{page_range.end_page})",
            )

            # Pipeline A
            log.info("pipeline_a_start", doc=i + 1, pages=f"{page_range.start_page}-{page_range.end_page}")
            result_a = run_pipeline_a(doc_pages)

            # Pipeline B
            log.info("pipeline_b_start", doc=i + 1)
            result_b = run_pipeline_b(doc_pages)

            # Reconcile
            recon = reconcile(result_a, result_b)

            record = DocumentRecord(
                source_file_id=source_file_id,
                doc_id=doc_id,
                page_start=page_range.start_page,
                page_end=page_range.end_page,
                # Pipeline A
                supplier_a=result_a.supplier,
                po_primary_a=result_a.po_primary,
                po_secondary_a=result_a.po_secondary,
                po_numbers_a=result_a.po_numbers,
                confidence_a=result_a.confidence,
                method_a=result_a.method.value,
                # Pipeline B
                supplier_b=result_b.supplier,
                po_primary_b=result_b.po_primary,
                po_secondary_b=result_b.po_secondary,
                po_numbers_b=result_b.po_numbers,
                confidence_b=result_b.confidence,
                method_b=result_b.method.value,
                # Reconciliation
                match_status=recon.match_status,
                decided_po_primary=recon.decided_po_primary,
                decided_po_secondary=recon.decided_po_secondary,
                decided_po_numbers=recon.decided_po_numbers,
                status=recon.status,
                next_action=recon.next_action,
                reject_reason=recon.reject_reason,
            )
            all_records.append(record)

            log.info(
                "doc_processed",
                doc=i + 1,
                status=recon.status.value,
                match=recon.match_status.value,
                po=recon.decided_po_primary,
            )

        # Save extraction artifacts
        storage.save_artifact(source_file_id, "extract_A", [
            {"range": {"start_page": r.page_start, "end_page": r.page_end},
             "po_primary": r.po_primary_a, "po_secondary": r.po_secondary_a,
             "po_numbers": r.po_numbers_a,
             "confidence": r.confidence_a, "method": r.method_a}
            for r in all_records
        ])
        storage.save_artifact(source_file_id, "extract_B", [
            {"range": {"start_page": r.page_start, "end_page": r.page_end},
             "po_primary": r.po_primary_b, "po_secondary": r.po_secondary_b,
             "po_numbers": r.po_numbers_b,
             "confidence": r.confidence_b, "method": r.method_b}
            for r in all_records
        ])
        storage.save_artifact(source_file_id, "reconcile", [
            {"doc_id": r.doc_id, "match_status": r.match_status.value if r.match_status else None,
             "decided_po_primary": r.decided_po_primary, "status": r.status.value if r.status else None,
             "next_action": r.next_action.value if r.next_action else None,
             "reject_reason": r.reject_reason}
            for r in all_records
        ])

        # Step 6: Generate Excel
        update_job(job_id, progress=0.85, current_step="Generating Excel")
        excel_path = generate_index_excel(source_file_id, all_records)
        log.info("excel_generated", path=str(excel_path))

        # Step 7: Create reject records for NOT_OK cases
        update_job(job_id, progress=0.90, current_step="Creating reject records")
        reject_count = 0
        for record in all_records:
            if record.status == FinalStatus.NOT_OK:
                _create_reject_record(record)
                reject_count += 1
        log.info("rejects_created", count=reject_count)

        # Done
        total_ok = sum(1 for r in all_records if r.status == FinalStatus.OK)
        total_not_ok = sum(1 for r in all_records if r.status == FinalStatus.NOT_OK)

        result = {
            "total_documents": len(all_records),
            "total_ok": total_ok,
            "total_not_ok": total_not_ok,
            "excel_path": str(excel_path),
            "documents": [r.model_dump() for r in all_records],
        }

        update_job(
            job_id,
            status=JobStatus.COMPLETED,
            progress=1.0,
            current_step="Completed",
            result=result,
        )
        log.info(
            "process_completed",
            total_ok=total_ok,
            total_not_ok=total_not_ok,
        )

    except Exception as exc:
        log.error("process_failed", error=str(exc), exc_info=True)
        update_job(
            job_id,
            status=JobStatus.FAILED,
            current_step="Failed",
            error=str(exc),
        )


def _create_reject_record(record: DocumentRecord) -> None:
    """Create a reject record for a NOT_OK document (file-based)."""
    import json
    import uuid as uuid_mod
    from datetime import datetime, timezone
    from pathlib import Path

    from app.config import settings
    from app.schemas.common import PipelineMethod

    d = Path(settings.storage_base_path) / "rejects"
    d.mkdir(parents=True, exist_ok=True)

    reject_id = str(uuid_mod.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    reject = {
        "reject_id": reject_id,
        "source_file_id": record.source_file_id,
        "doc_id": record.doc_id,
        "page_start": record.page_start,
        "page_end": record.page_end,
        "result_a": {
            "po_primary": record.po_primary_a,
            "po_secondary": record.po_secondary_a,
            "supplier": record.supplier_a,
            "confidence": record.confidence_a,
            "method": record.method_a or "LLM",
            "found_keywords": [],
            "evidence": [],
        },
        "result_b": {
            "po_primary": record.po_primary_b,
            "po_secondary": record.po_secondary_b,
            "supplier": record.supplier_b,
            "confidence": record.confidence_b,
            "method": record.method_b or "REGEX",
            "found_keywords": [],
            "evidence": [],
        },
        "match_status": record.match_status.value if record.match_status else "NEEDS_REVIEW",
        "reject_reason": record.reject_reason,
        "resolved": False,
        "resolved_po": None,
        "created_at": now,
        "updated_at": now,
    }

    path = d / f"{reject_id}.json"
    path.write_text(json.dumps(reject, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
