package devsecops.release_readiness

release_gate if {
  input.release_candidate == true
}

approved_waiver(object_id) if {
  waiver := input.waivers[_]
  waiver.object_id == object_id
  waiver.status == "approved"
  waiver.expired == false
}

deny contains msg if {
  release_gate
  input.repository.protected_branch == true
  input.repository.direct_push_allowed == true
  msg := "DSCB-L1-REQ-003: Direct modification of protected branches is prohibited."
}

deny contains msg if {
  release_gate
  input.repository.protected_branch == true
  not input.repository.review_required
  msg := "DSCB-L1-REQ-003: Protected branch integration requires review."
}

deny contains msg if {
  release_gate
  not input.evidence.sbom.exists
  msg := "DSCB-L1-REQ-006: Release candidates require an SBOM."
}

deny contains msg if {
  release_gate
  input.evidence.sbom.exists
  not input.evidence.sbom.linked_to_artifact
  msg := "DSCB-L1-REQ-006: SBOM must be linked to the releasable artifact."
}

deny contains msg if {
  release_gate
  not input.evidence.vulnerability_scan.exists
  msg := "DSCB-L1-REQ-009: Release candidates require vulnerability scan evidence."
}

deny contains msg if {
  release_gate
  vuln := input.vulnerabilities[_]
  vuln.severity == "critical"
  not approved_waiver(vuln.id)
  msg := sprintf("DSCB-L1-REQ-010: Critical vulnerability %s requires an approved waiver.", [vuln.id])
}

deny contains msg if {
  release_gate
  not input.artifact.digest.exists
  not input.artifact.signature.exists
  msg := "DSCB-L1-REQ-011: Releasable artifacts require checksum, digest, or signature evidence."
}

deny contains msg if {
  release_gate
  input.artifact.digest.exists
  not input.artifact.digest.linked_to_artifact
  msg := "DSCB-L1-REQ-011: Artifact digest must be linked to the releasable artifact."
}

deny contains msg if {
  release_gate
  input.pipeline.external_direct_downloads_detected == true
  msg := "DSCB-L2-REQ-006: Direct downloads from external sources are not permitted."
}

deny contains msg if {
  release_gate
  dep := input.dependencies[_]
  dep.source_approved == false
  not approved_waiver(dep.name)
  msg := sprintf("DSCB-L2-REQ-006: Dependency %s is not retrieved from an approved source.", [dep.name])
}

deny contains msg if {
  release_gate
  input.deployment.required == true
  not input.infrastructure.iac_repository.exists
  msg := "DSCB-L2-REQ-009: Deployment infrastructure must be defined through Infrastructure as Code."
}

deny contains msg if {
  release_gate
  input.infrastructure.iac_repository.exists
  not input.infrastructure.iac_repository.version_controlled
  msg := "DSCB-L2-REQ-010: Infrastructure definitions must be maintained in version control."
}

deny contains msg if {
  release_gate
  not input.pipeline.security_gates.enforced
  msg := "DSCB-L2-REQ-011: DevSecOps pipelines must enforce security gates."
}

deny contains msg if {
  release_gate
  input.pipeline.security_thresholds_exceeded == true
  not input.release.approved_waiver.exists
  msg := "DSCB-L2-REQ-012: Releases must not proceed when defined security thresholds are exceeded unless an approved waiver exists."
}

deny contains msg if {
  waiver := input.waivers[_]
  waiver.status == "approved"
  waiver.expired == true
  msg := sprintf("DSCB-GOV-REQ-005: Waiver %s is expired and must not be used.", [waiver.id])
}

deny contains msg if {
  waiver := input.waivers[_]
  waiver.status == "approved"
  not waiver.risk_classification
  msg := sprintf("DSCB-GOV-REQ-005: Waiver %s requires risk classification.", [waiver.id])
}

deny contains msg if {
  waiver := input.waivers[_]
  waiver.status == "approved"
  not waiver.compensating_controls
  msg := sprintf("DSCB-GOV-REQ-005: Waiver %s requires compensating controls.", [waiver.id])
}
