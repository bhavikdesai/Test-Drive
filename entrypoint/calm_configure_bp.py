"""
calm_configure_bp.py: automation to configure
blueprints on NX-on-GCP / Test Drive.

Author: michael@nutanix.com
Date:   2020-03-09
"""

import sys
import os
import json

sys.path.append(os.path.join(os.getcwd(), "nutest_gcp.egg"))

from framework.lib.nulog import INFO, ERROR
from helpers.rest import RequestResponse
from helpers.calm import (file_to_dict, get_subnet_info,
                          body_via_v3_get, body_via_v3_post,
                          update_via_v3_put)

def main():

  # Get and log the config from the Env variable
  config = json.loads(os.environ["CUSTOM_SCRIPT_CONFIG"])
  INFO(config)

  # Get PC info from the config dict
  pc_info = config.get("tdaas_pc")
  pc_external_ip = pc_info.get("ips")[0][0]
  pc_internal_ip = pc_info.get("ips")[0][1]
  pc_password = pc_info.get("prism_password")

  try:

    # Read in the spec files and conver to dicts
    subnet_spec = file_to_dict("specs/calm_subnet.spec")
    INFO(f"subnet_spec: {subnet_spec}")
    secret_spec = file_to_dict("specs/calm_secrets.spec")
    INFO(f"secret_spec: {secret_spec}")

    # Get our subnet and image info from the infra
    subnet_info = get_subnet_info(pc_external_ip, pc_password,
                                  subnet_spec["vlan"])
    image_info = body_via_v3_post(pc_external_ip, "images",
                                  pc_password, None).json

    # Get a list of DRAFT blueprints
    payload = {
      "filter": "state==DRAFT"
    }
    draft_resp = body_via_v3_post(pc_external_ip, "blueprints",
                                  pc_password, payload).json

    # Loop through the blueprints to modify
    for bp in draft_resp["entities"]:

      # Get the body of our blueprint
      bp_body = body_via_v3_get(pc_external_ip, "blueprints",
                                pc_password, bp["metadata"]["uuid"]).json

      # Remove unneeded status
      del bp_body["status"]

      # Configure secrets
      for secret in bp_body["spec"]["resources"]\
                           ["credential_definition_list"]:
        secret["secret"]["attrs"]["is_secret_modified"] = True
        # Handle PC Creds which are unique
        if secret["name"] == "PC_CREDS":
          secret["secret"]["username"] = "admin"
          secret["secret"]["value"] = pc_password
        # Find a matching type/username from our secret_spec
        else:
          for ss in secret_spec["entities"]:
            if secret["type"] == ss["type"] and\
               secret["username"] == ss["username"]:
              secret["secret"]["value"] = ss["secret"]
        print(json.dumps(secret, sort_keys=True, indent=4))

      # Configure NICs and Images
      for substrate in bp_body["spec"]["resources"]["substrate_definition_list"]:
        if substrate["type"] == "AHV_VM":
          for nic in substrate["create_spec"]["resources"]["nic_list"]:
            nic["subnet_reference"]["uuid"] = subnet_info["uuid"]
            nic["subnet_reference"]["name"] = subnet_info["name"]
            print(json.dumps(nic, sort_keys=True, indent=4))
          for disk in substrate["create_spec"]["resources"]["disk_list"]:
            if disk["data_source_reference"] is not None and\
               disk["data_source_reference"]["kind"] == "image":
              for image in image_info["entities"]:
                if image["status"]["name"] == disk["data_source_reference"]["name"]:
                  disk["data_source_reference"]["uuid"] = image["metadata"]["uuid"]
                  print(json.dumps(disk, sort_keys=True, indent=4))

      # Update our blueprint
      resp = update_via_v3_put(pc_external_ip, "blueprints", pc_password,
                               bp["metadata"]["uuid"], bp_body)

      # Log appropriately based on response
      if (resp.code == 200 or resp.code == 202):
        INFO(f"{bp['metadata']['name']} blueprint updated successfully.")
      else:
        raise Exception(f"{bp['metadata']['name']} blueprint update" +
                        f" failed with:\n" +
                        f"Error Code: {resp.code}\n" +
                        f"Error Message: {resp.message}")

  except Exception as ex:
    INFO(ex)

if __name__ == '__main__':
  main()

