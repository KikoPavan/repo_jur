import json
import logging
import os
import shutil
import tempfile
from pathlib import Path
from datetime import datetime, timezone

from .config import IngressConfig, IntakeConfig
from .contracts import (
    CriticalValidationStatus,
    GateState,
    Phase1Artifacts,
    RouteTarget,
)
from .converter import convert_document
from .domain_router import (
    RoutingContext,
    build_routing_record,
    route,
    routing_state_filename,
)
from .evidence import LocalFilesystemObjectStorageGateway
from .ingress import PreflightLimits, preflight_envelope
from .intake_builder import ITPBuilder
from .intake_manager import IntakeManager, IntakeRegistryEntry, IntakeState
from .legal_producer import (
    LegalConceptType,
    ProducerContext,
    DuplicateResolution,
    produce,
    LegalProducerBlockedError,
)
from .legal_semantic_review import (
    LegalReviewProfile,
    LegalSemanticReviewEngine,
)
from .quality_gate import evaluate
from .report import attach_gate_result
from .models import Relatorio


class IntakeOrchestrator:
    def __init__(
        self,
        intake_config: IntakeConfig,
        ingress_config: IngressConfig,
        logger: logging.Logger,
        bundle_root: str | Path = "bundle"
    ):
        self.intake_manager = IntakeManager(intake_config)
        self.itp_builder = ITPBuilder(ingress_config.inbox_dir)
        self.ingress_config = ingress_config
        self.logger = logger
        self.output_dir = Path("output")
        self.logs_dir = Path("logs")
        self._bundle_root_str = str(bundle_root)

    @property
    def bundle_root(self) -> Path:
        return Path(self._bundle_root_str).resolve()

    def _safe_write(self, content: str, path: Path):
        """Atomic write without using the project's validator.write_atomic."""
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_path = tempfile.mkstemp(dir=str(path.parent), prefix="tmp-intake-")
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp_path, str(path))
        except Exception:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise

    def scan_and_process(self):
        input_dir = self.intake_manager.config.input_dir
        if not input_dir.exists():
            self.logger.warning(f"Diretório de entrada {input_dir} não existe.")
            return

        self.reconcile()

        for item in sorted(input_dir.iterdir()):
            if item.is_file() and item.suffix == ".pdf":
                 self.logger.warning(f"SKIP_UNCLASSIFIED: {item.name} está na raiz de input/. Mova para um subdiretório de tipo.")

        subdirs = ["legislacao", "jurisprudencia", "temas", "precedentes"]
        for subdir in subdirs:
            target_dir = input_dir / subdir
            if not target_dir.exists():
                continue

            for pdf_path in sorted(target_dir.glob("*.pdf")):
                self.logger.info(f"Processando entrada operacional: {subdir}/{pdf_path.name}")
                entry = self.intake_manager.claim_file(pdf_path)
                if not entry:
                    continue

                if entry.state == IntakeState.PUBLISHED:
                    if self.verify_published_integrity(entry):
                        self.logger.info(f"SHA-256 {entry.sha256} já publicado e íntegro. Descartando duplicata.")
                        proc_pdf = self.intake_manager.config.processing_dir / f"{entry.sha256}.pdf"
                        if proc_pdf.exists():
                            proc_pdf.unlink()
                        continue
                    else:
                        self.logger.error(f"Inconsistência para {entry.sha256}. Movido para FAILED.")
                        entry.state = IntakeState.FAILED
                        entry.last_error = {"message": "Publicação original ausente ou corrompida", "stage": "VERIFY"}
                        self.preserve_failure(entry)
                        continue

                self.process_entry(entry)

    def reconcile(self):
        for registry_file in sorted(self.intake_manager.config.registry_dir.glob("*.json")):
            sha = registry_file.stem
            entry = self.intake_manager.load_entry(sha)
            if not entry or entry.state in (IntakeState.PUBLISHED, IntakeState.FAILED):
                continue

            if entry.lease and self.intake_manager.is_lease_stale(entry.lease):
                self.logger.info(f"Recuperando entrada interrompida {sha} ({entry.state})")
                entry.lease = self.intake_manager.create_lease()
                self.intake_manager.save_entry_atomic(entry)
                self.process_entry(entry)

    def verify_published_integrity(self, entry: IntakeRegistryEntry) -> bool:
        if not entry.evidence_reference:
            return False
        ev_path = self.ingress_config.object_storage_root / entry.evidence_reference
        if not ev_path.exists():
            return False
        if entry.concept_id:
            concept_path = self.bundle_root / entry.concept_id
            if not concept_path.exists():
                return False
        return True

    def preserve_failure(self, entry: IntakeRegistryEntry):
        proc_pdf = self.intake_manager.config.processing_dir / f"{entry.sha256}.pdf"
        if proc_pdf.exists():
            dest = self.intake_manager.config.failed_dir / f"{entry.sha256}.pdf"
            shutil.move(str(proc_pdf), str(dest))
        self.intake_manager.save_entry_atomic(entry)

    def process_entry(self, entry: IntakeRegistryEntry):
        from dataclasses import asdict
        try:
            self.intake_manager.update_heartbeat(entry)

            # 1. Ingress
            if entry.state == IntakeState.PROCESSING:
                pdf_path = self.intake_manager.config.processing_dir / f"{entry.sha256}.pdf"
                if not pdf_path.exists():
                    zip_path = self.ingress_config.inbox_dir / f"{entry.handoff_id}.zip"
                    if not zip_path.exists():
                        raise FileNotFoundError(f"PDF ausente em processing/ para {entry.sha256}")
                else:
                    zip_path = self.itp_builder.build_envelope(pdf_path, entry.manifest_data)

                storage = LocalFilesystemObjectStorageGateway(self.ingress_config.object_storage_root)
                preflight_result = preflight_envelope(zip_path, self.ingress_config, PreflightLimits.from_env(), storage)
                entry.evidence_reference = preflight_result.evidence_reference
                entry.state = IntakeState.PRESERVED
                self.intake_manager.save_entry_atomic(entry)
                if zip_path.exists():
                    zip_path.unlink()

            self.intake_manager.update_heartbeat(entry)

            if not entry.evidence_reference:
                 raise RuntimeError("Referência de evidência ausente após preservação.")

            preserved_pdf = self.ingress_config.object_storage_root / entry.evidence_reference
            md_path = self.output_dir / f"{entry.handoff_id}.md"
            rep_path = self.logs_dir / f"{entry.handoff_id}.report.json"

            markdown, report = convert_document(
                pdf_path=preserved_pdf,
                output_path=md_path,
                temp_root="var/tmp",
                allow_partial=True,
                use_ocr=True,
                ocr_api_key=os.environ.get("GEMINI_API_KEY"),
                ocr_model=os.environ.get("GEMINI_MODEL"),
            )

            artifacts = Phase1Artifacts(markdown, json.dumps(asdict(report)))
            gate_result = evaluate(artifacts)

            final_report = attach_gate_result(
                report,
                quality_gate=gate_result.state.value,
                warnings=gate_result.warnings,
                errors=gate_result.errors
            )
            report_json = json.dumps(asdict(final_report))
            # Requisito: Não usar write_atomic da Intake
            self._safe_write(report_json, rep_path)

            self.intake_manager.update_heartbeat(entry)

            # 3. Domain Router
            context = RoutingContext(requested_domain=RouteTarget.LEGAL_KNOWLEDGE)
            decision = route(Phase1Artifacts(markdown, report_json), critical_status=CriticalValidationStatus.OK, routing_context=context)

            # 4. Legal Knowledge Flow
            if decision.target == RouteTarget.LEGAL_KNOWLEDGE:
                # Semantic Review
                review_engine = LegalSemanticReviewEngine()
                review_result = review_engine.review(Phase1Artifacts(markdown, report_json), LegalReviewProfile("default", "1.0", ()))

                if not entry.okf_type:
                     raise RuntimeError(f"Tipo OKF não definido para {entry.sha256}.")

                prod_context = ProducerContext(type=entry.okf_type, evidence_resource=entry.evidence_reference)

                # Requisito 1: Usar produce() público
                result = produce(
                    Phase1Artifacts(markdown, report_json),
                    decision,
                    review_result,
                    prod_context,
                    bundle_root=self.bundle_root,
                    overwrite=True
                )

                # Handle results
                if result.resolution in (DuplicateResolution.NEW_CONCEPT, DuplicateResolution.REGENERATE, DuplicateResolution.NOOP):
                    if result.concept_path:
                        entry.concept_id = str(result.concept_path.resolve().relative_to(self.bundle_root))

                    if result.written or result.resolution == DuplicateResolution.NOOP:
                         entry.state = IntakeState.PUBLISHED
                         self.intake_manager.save_entry_atomic(entry)

                         proc_pdf = self.intake_manager.config.processing_dir / f"{entry.sha256}.pdf"
                         if proc_pdf.exists():
                             proc_pdf.unlink()
                         self.logger.info(f"Publicado: {entry.concept_id}")
                    else:
                         self.logger.warning(f"Producer resolveu como {result.resolution} mas não efetivou escrita.")
                         entry.state = IntakeState.PRESERVED
                         self.intake_manager.save_entry_atomic(entry)

                elif result.resolution == DuplicateResolution.HUMAN_REVIEW:
                    self.logger.warning(f"REVISÃO HUMANA NECESSÁRIA para {entry.sha256}. Documento preservado.")
                    entry.state = IntakeState.PRESERVED # Permanece preservado para revisão
                    self.intake_manager.save_entry_atomic(entry)

            else:
                self.logger.warning(f"Domínio {decision.target} não suportado para auto-publish.")

        except LegalProducerBlockedError as e:
            if e.reason == "review_required":
                self.logger.warning(f"BLOQUEIO DO PRODUCER: Revisão necessária para {entry.sha256}. Estado: PRESERVED.")
                entry.state = IntakeState.PRESERVED
                self.intake_manager.save_entry_atomic(entry)
            else:
                raise

        except Exception as e:
            self.logger.exception(f"Erro ao processar {entry.sha256}")
            entry.state = IntakeState.FAILED
            entry.last_error = {"message": str(e), "stage": "ORCHESTRATION"}
            self.preserve_failure(entry)
