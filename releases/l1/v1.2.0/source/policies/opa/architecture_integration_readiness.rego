package architecture.integration_readiness

integration_gate if {
  input.release_candidate == true
}

integration_marker_ids := {"E3", "E5", "S3", "S4", "S5", "S7", "P4", "P5", "P6"}

marker_score(marker_id) := score if {
  marker := input.architecture.marker_assessments[_]
  marker.id == marker_id
  score := marker.score
}

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

deny contains msg if {
  integration_gate
  marker_id := integration_marker_ids[_]
  not marker_score(marker_id)
  not has_valid_exception(marker_id)
  msg := sprintf("RG-INTEGRATION-READY: Integration-readiness marker %s is missing and has no valid exception.", [marker_id])
}

deny contains msg if {
  integration_gate
  marker_id := integration_marker_ids[_]
  score := marker_score(marker_id)
  score < 3
  not has_valid_exception(marker_id)
  msg := sprintf("RG-INTEGRATION-READY: Integration-readiness marker %s requires score 3 or a valid exception; current score is %v.", [marker_id, score])
}

deny contains msg if {
  integration_gate
  not input.architecture.compatibility_evidence.exists
  msg := "RG-INTEGRATION-READY: Integration readiness requires compatibility evidence."
}

deny contains msg if {
  integration_gate
  not input.architecture.deployment_evidence.exists
  msg := "RG-INTEGRATION-READY: Integration readiness requires deployment evidence."
}
