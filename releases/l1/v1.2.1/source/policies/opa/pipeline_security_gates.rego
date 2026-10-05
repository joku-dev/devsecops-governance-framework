package devsecops.pipeline_security_gates

import rego.v1

deny contains msg if {
  input.release_candidate == true
  not input.pipeline.security_gates.enforced
  msg := "DSCB-L2-REQ-011: DevSecOps pipelines must enforce security gates."
}

deny contains msg if {
  input.release_candidate == true
  input.pipeline.security_thresholds_exceeded == true
  not input.release.approved_waiver.exists
  msg := "DSCB-L2-REQ-012: Releases must not proceed when defined security thresholds are exceeded unless an approved waiver exists."
}
