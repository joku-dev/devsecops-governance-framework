package devsecops.artifact_integrity

import rego.v1

deny contains msg if {
  input.release_candidate == true
  not input.artifact.digest.exists
  not input.artifact.signature.exists
  msg := "DSCB-L1-REQ-011: Releasable artifacts require checksum, digest, or signature evidence."
}

deny contains msg if {
  input.release_candidate == true
  input.artifact.digest.exists
  not input.artifact.digest.linked_to_artifact
  msg := "DSCB-L1-REQ-011: Artifact digest must be linked to the releasable artifact."
}
