package devsecops.iac

import rego.v1

deny contains msg if {
  input.deployment.required == true
  not input.infrastructure.iac_repository.exists
  msg := "DSCB-L2-REQ-009: Deployment infrastructure must be defined through Infrastructure as Code."
}

deny contains msg if {
  input.infrastructure.iac_repository.exists
  not input.infrastructure.iac_repository.version_controlled
  msg := "DSCB-L2-REQ-010: Infrastructure definitions must be maintained in version control."
}
