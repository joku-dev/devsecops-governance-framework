package devsecops.artifact_signing

import rego.v1

deny contains msg if {
  input.release_candidate == true
  input.required_platform_level == "PRA-Level 2"
  not input.artifact.signature.exists
  msg := "DSCB-L2-REQ-007: Software artifacts must be cryptographically signed before release."
}

deny contains msg if {
  input.artifact.signature.exists
  not input.signing.keys_protected
  msg := "DSCB-L2-REQ-008: Signing keys must be protected and managed according to enterprise security policies."
}
