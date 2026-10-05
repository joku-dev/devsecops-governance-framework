package architecture.readiness

architecture_gate if {
  input.release_candidate == true
}

architecture_readiness_marker_ids := {"B1", "B2", "B3", "B4", "P0", "P1", "P2", "P3", "P7", "S0", "S1", "S2"}

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
  architecture_gate
  marker_id := architecture_readiness_marker_ids[_]
  not marker_score(marker_id)
  not has_valid_exception(marker_id)
  msg := sprintf("RG-ARCH-READY: Architecture-readiness marker %s is missing and has no valid exception.", [marker_id])
}

deny contains msg if {
  architecture_gate
  marker_id := architecture_readiness_marker_ids[_]
  score := marker_score(marker_id)
  score < 3
  not has_valid_exception(marker_id)
  msg := sprintf("RG-ARCH-READY: Architecture-readiness marker %s requires score 3 or a valid exception; current score is %v.", [marker_id, score])
}
