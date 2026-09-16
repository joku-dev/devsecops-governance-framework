package architecture.operation_readiness

operation_gate if {
  input.release_candidate == true
}

operation_marker_ids := {"B5", "P11"}

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
  operation_gate
  marker_id := operation_marker_ids[_]
  not marker_score(marker_id)
  not has_valid_exception(marker_id)
  msg := sprintf("RG-OPERATION-READY: Operation-readiness marker %s is missing and has no valid exception.", [marker_id])
}

deny contains msg if {
  operation_gate
  marker_id := operation_marker_ids[_]
  score := marker_score(marker_id)
  score < 4
  not has_valid_exception(marker_id)
  msg := sprintf("RG-OPERATION-READY: Operation-readiness marker %s requires score 4 or a valid exception; current score is %v.", [marker_id, score])
}

deny contains msg if {
  operation_gate
  not input.architecture.runtime_evidence.exists
  msg := "RG-OPERATION-READY: Operation readiness requires runtime evidence."
}

deny contains msg if {
  operation_gate
  not input.architecture.feedback_evidence.exists
  msg := "RG-OPERATION-READY: Operation readiness requires feedback evidence."
}
