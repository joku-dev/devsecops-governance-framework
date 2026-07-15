package devsecops.access_control

import rego.v1

deny contains msg if {
  input.platform.privileged_access == true
  not input.platform.mfa_enforced
  msg := "DSCB-L2-REQ-004: Multi-factor authentication must be enforced for privileged access."
}

deny contains msg if {
  input.platform.central_identity_management == false
  msg := "DSCB-L2-REQ-003: DevSecOps platform access must be controlled through centralized identity management."
}
