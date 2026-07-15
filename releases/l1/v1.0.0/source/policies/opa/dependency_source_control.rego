package devsecops.dependency_source_control

import rego.v1

deny contains msg if {
  dep := input.dependencies[_]
  dep.source_approved == false
  not approved_waiver(dep.name)
  msg := sprintf("DSCB-L2-REQ-006: Dependency %s is not retrieved from an approved source.", [dep.name])
}

deny contains msg if {
  input.pipeline.external_direct_downloads_detected == true
  msg := "DSCB-L2-REQ-006: Direct downloads from external sources are not permitted."
}

approved_waiver(object_id) if {
  waiver := input.waivers[_]
  waiver.object_id == object_id
  waiver.status == "approved"
  waiver.expired == false
}
