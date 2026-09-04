import json
import os
import tempfile
import zipfile
from pathlib import Path
from .intake_manager import ManifestData

class ITPBuilder:
    def __init__(self, inbox_dir: Path):
        self.inbox_dir = inbox_dir

    def build_envelope(self, pdf_path: Path, manifest_data: ManifestData) -> Path:
        handoff_id = manifest_data.handoff_id
        zip_filename = f"{handoff_id}.zip"
        partial_path = self.inbox_dir / f"{handoff_id}.partial"
        final_path = self.inbox_dir / zip_filename

        # Create ZIP
        with zipfile.ZipFile(partial_path, "w", zipfile.ZIP_DEFLATED) as zf:
            # manifest.json
            manifest_dict = {
                "protocol_version": "1.0",
                "handoff_id": manifest_data.handoff_id,
                "evidence_reference": "evidence.pdf",
                "source_origin": manifest_data.source_origin,
                "retrieved_at": manifest_data.retrieved_at,
                "collector": "process:pipeline-juridico-intake",
                "media_type": "application/pdf",
                "byte_size": manifest_data.byte_size,
            }
            if manifest_data.last_modified:
                manifest_dict["last_modified"] = manifest_data.last_modified
            manifest_dict["candidate_sha256"] = manifest_data.candidate_sha256

            zf.writestr("manifest.json", json.dumps(manifest_dict, indent=2, sort_keys=True))

            # evidence.pdf
            zf.write(pdf_path, "evidence.pdf")

        # Atomic rename
        os.replace(partial_path, final_path)
        return final_path
