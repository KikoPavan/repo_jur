from __future__ import annotations

import json
import os
import shutil
import socket
import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import IntakeConfig
from .hashing import sha256_file
from .legal_producer import LegalConceptType

class IntakeState(str, Enum):
    PROCESSING = "PROCESSING"
    PRESERVED = "PRESERVED"
    FAILED = "FAILED"
    PUBLISHED = "PUBLISHED"

@dataclass
class ManifestData:
    handoff_id: str
    retrieved_at: str
    source_origin: str
    candidate_sha256: str
    byte_size: int
    last_modified: Optional[str] = None

@dataclass
class IntakeLease:
    claim_id: str
    owner_pid: int
    owner_host: str
    claimed_at: str
    heartbeat_at: str

@dataclass
class ObservedSource:
    name: str
    path: str
    timestamp: str

@dataclass
class IntakeRegistryEntry:
    sha256: str
    state: IntakeState
    handoff_id: str
    manifest_data: ManifestData
    okf_type: Optional[LegalConceptType] = None
    lease: Optional[IntakeLease] = None
    observed_sources: List[ObservedSource] = field(default_factory=list)
    evidence_reference: Optional[str] = None
    concept_id: Optional[str] = None
    last_error: Optional[Dict[str, str]] = None

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, sort_keys=True)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> IntakeRegistryEntry:
        data = data.copy()
        data["state"] = IntakeState(data["state"])
        data["manifest_data"] = ManifestData(**data["manifest_data"])
        if data.get("okf_type"):
            data["okf_type"] = LegalConceptType(data["okf_type"])
        if data.get("lease"):
            data["lease"] = IntakeLease(**data["lease"])
        if data.get("observed_sources"):
            data["observed_sources"] = [ObservedSource(**s) for s in data["observed_sources"]]
        return cls(**data)

class IntakeManager:
    TYPE_MAPPING = {
        "legislacao": LegalConceptType.Legislacao,
        "jurisprudencia": LegalConceptType.Jurisprudencia,
        "temas": LegalConceptType.TemaJuridico,
        "precedentes": LegalConceptType.PrecedenteVinculante,
    }

    def __init__(self, config: IntakeConfig, claim_id: Optional[str] = None):
        self.config = config
        self.claim_id = claim_id or str(uuid.uuid4())
        self.host = socket.gethostname()
        self.pid = os.getpid()

    def get_registry_path(self, sha256: str) -> Path:
        return self.config.registry_dir / f"{sha256}.json"

    def load_entry(self, sha256: str) -> Optional[IntakeRegistryEntry]:
        path = self.get_registry_path(sha256)
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            return IntakeRegistryEntry.from_dict(json.load(f))

    def save_entry_atomic(self, entry: IntakeRegistryEntry) -> None:
        if entry.state in (IntakeState.PROCESSING, IntakeState.PRESERVED):
            if entry.lease and entry.lease.claim_id != self.claim_id:
                if not self.is_lease_stale(entry.lease):
                    raise RuntimeError(
                        f"Negado: claim_id {self.claim_id} não possui o lease ativo para {entry.sha256}"
                    )

        path = self.get_registry_path(entry.sha256)
        temp_path = path.with_suffix(".tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(entry.to_json())
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_path, path)

    def is_lease_stale(self, lease: IntakeLease) -> bool:
        from datetime import datetime, timezone
        try:
            heartbeat_dt = datetime.fromisoformat(lease.heartbeat_at)
            if heartbeat_dt.tzinfo is None:
                heartbeat_dt = heartbeat_dt.replace(tzinfo=timezone.utc)
        except ValueError:
            return True
        now = datetime.now(timezone.utc)
        if (now - heartbeat_dt).total_seconds() > self.config.lease_timeout_seconds:
            return True
        if lease.owner_host == self.host:
            try:
                os.kill(lease.owner_pid, 0)
            except OSError:
                return True
        return False

    def create_lease(self) -> IntakeLease:
        from datetime import datetime, timezone
        now_iso = datetime.now(timezone.utc).isoformat()
        return IntakeLease(
            claim_id=self.claim_id,
            owner_pid=self.pid,
            owner_host=self.host,
            claimed_at=now_iso,
            heartbeat_at=now_iso
        )

    def update_heartbeat(self, entry: IntakeRegistryEntry):
        if entry.lease and entry.lease.claim_id == self.claim_id:
            from datetime import datetime, timezone
            entry.lease.heartbeat_at = datetime.now(timezone.utc).isoformat()
            self.save_entry_atomic(entry)

    def claim_file(self, pdf_path: Path) -> Optional[IntakeRegistryEntry]:
        if pdf_path.suffix == ".partial":
            return None

        parent_name = pdf_path.parent.name
        okf_type = self.TYPE_MAPPING.get(parent_name)
        if not okf_type and pdf_path.parent == self.config.input_dir:
            return None

        sha256 = sha256_file(pdf_path)
        entry = self.load_entry(sha256)
        from datetime import datetime, timezone
        now_iso = datetime.now(timezone.utc).isoformat()

        if entry:
            if entry.state == IntakeState.PUBLISHED:
                pass
            elif entry.state in (IntakeState.PROCESSING, IntakeState.PRESERVED):
                if entry.lease and not self.is_lease_stale(entry.lease):
                    if entry.lease.claim_id != self.claim_id:
                        return None

            if entry.state in (IntakeState.PUBLISHED, IntakeState.FAILED):
                entry.handoff_id = str(uuid.uuid4())
                entry.state = IntakeState.PROCESSING
                entry.manifest_data.handoff_id = entry.handoff_id
                entry.manifest_data.retrieved_at = now_iso
                entry.manifest_data.source_origin = str(pdf_path)
                entry.okf_type = okf_type

            entry.lease = self.create_lease()
            entry.observed_sources.append(ObservedSource(pdf_path.name, str(pdf_path), now_iso))
        else:
            mtime = datetime.fromtimestamp(pdf_path.stat().st_mtime, timezone.utc).isoformat()
            handoff_id = str(uuid.uuid4())
            manifest = ManifestData(
                handoff_id=handoff_id,
                retrieved_at=now_iso,
                source_origin=str(pdf_path),
                candidate_sha256=sha256,
                byte_size=pdf_path.stat().st_size,
                last_modified=mtime
            )
            entry = IntakeRegistryEntry(
                sha256=sha256,
                state=IntakeState.PROCESSING,
                handoff_id=handoff_id,
                manifest_data=manifest,
                okf_type=okf_type,
                lease=self.create_lease(),
                observed_sources=[ObservedSource(pdf_path.name, str(pdf_path), now_iso)]
            )

        target_path = self.config.processing_dir / f"{sha256}.pdf"
        try:
            os.replace(pdf_path, target_path)
        except OSError:
            shutil.move(str(pdf_path), str(target_path))

        self.save_entry_atomic(entry)
        return entry
