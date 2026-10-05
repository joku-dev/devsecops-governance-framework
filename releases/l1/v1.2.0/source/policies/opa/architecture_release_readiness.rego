package architecture.release_readiness

release_gate if {
  input.release_candidate == true
}

release_critical_marker_ids := {"E6", "E7", "E8", "S3", "S5", "S6", "S8", "P5", "P6", "P8", "P9", "P10", "P13"}

has_valid_exception(marker_id) if {
  exception := input.architecture.exceptions[_]
  exception.status == "approved"
  exception.expired == false
  exception.applies_to[_] == marker_id
  exception.owner
  exception.mitigation
  exception.risk_classification
  exception.review_date
  exception.expiry_date
  exception.approval_authority
}

marker_score(marker_id) := score if {
  marker := input.architecture.marker_assessments[_]
  marker.id == marker_id
  score := marker.score
}

deny contains msg if {
  release_gate
  marker_id := release_critical_marker_ids[_]
  not marker_score(marker_id)
  not has_valid_exception(marker_id)
  msg := sprintf("RG-RELEASE-READY: Release-critical architecture marker %s is missing and has no valid exception.", [marker_id])
}

deny contains msg if {
  release_gate
  marker_id := release_critical_marker_ids[_]
  score := marker_score(marker_id)
  score < 4
  not has_valid_exception(marker_id)
  msg := sprintf("RG-RELEASE-READY: Release-critical architecture marker %s requires score 4 or a valid exception; current score is %v.", [marker_id, score])
}

deny contains msg if {
  release_gate
  not input.architecture.release_compatibility_declaration.exists
  msg := "RG-RELEASE-READY: Release candidate requires a release compatibility declaration."
}

deny contains msg if {
  release_gate
  input.architecture.release_compatibility_declaration.exists
  not input.architecture.release_compatibility_declaration.baseline_version
  msg := "RG-RELEASE-READY: Release compatibility declaration requires a baseline version."
}

deny contains msg if {
  release_gate
  input.architecture.release_compatibility_declaration.exists
  not input.architecture.release_compatibility_declaration.approved
  msg := "RG-RELEASE-READY: Release compatibility declaration must be approved."
}

deny contains msg if {
  release_gate
  not input.architecture.solution_baseline.exists
  msg := "RG-RELEASE-READY: Release candidate requires a solution baseline."
}

deny contains msg if {
  release_gate
  not input.architecture.compatibility_evidence.exists
  msg := "RG-RELEASE-READY: Release candidate requires compatibility evidence."
}

deny contains msg if {
  release_gate
  not input.architecture.security_evidence.exists
  msg := "RG-RELEASE-READY: Release candidate requires security evidence."
}

deny contains msg if {
  release_gate
  not input.architecture.deployment_evidence.exists
  msg := "RG-RELEASE-READY: Release candidate requires deployment evidence."
}

deny contains msg if {
  release_gate
  exception := input.architecture.exceptions[_]
  exception.status == "approved"
  not exception.owner
  msg := sprintf("AG-EXC-001: Approved architecture exception %s requires an owner.", [exception.id])
}

deny contains msg if {
  release_gate
  exception := input.architecture.exceptions[_]
  exception.status == "approved"
  not exception.mitigation
  msg := sprintf("AG-EXC-001: Approved architecture exception %s requires mitigation.", [exception.id])
}

deny contains msg if {
  release_gate
  exception := input.architecture.exceptions[_]
  exception.status == "approved"
  not exception.risk_classification
  msg := sprintf("AG-EXC-001: Approved architecture exception %s requires risk classification.", [exception.id])
}

deny contains msg if {
  release_gate
  exception := input.architecture.exceptions[_]
  exception.status == "approved"
  not exception.review_date
  msg := sprintf("AG-EXC-001: Approved architecture exception %s requires a review date.", [exception.id])
}

deny contains msg if {
  release_gate
  exception := input.architecture.exceptions[_]
  exception.status == "approved"
  not exception.expiry_date
  msg := sprintf("AG-EXC-001: Approved architecture exception %s requires an expiry date.", [exception.id])
}

deny contains msg if {
  release_gate
  exception := input.architecture.exceptions[_]
  exception.status == "approved"
  not exception.approval_authority
  msg := sprintf("AG-EXC-001: Approved architecture exception %s requires an approval authority.", [exception.id])
}

deny contains msg if {
  release_gate
  exception := input.architecture.exceptions[_]
  exception.status == "approved"
  exception.expired == true
  msg := sprintf("AG-EXC-001: Approved architecture exception %s is expired and must not be used for release readiness.", [exception.id])
}
