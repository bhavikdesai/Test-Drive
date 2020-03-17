"""
calm_publish_bp.py: automation to publish blueprints into
the Marketplace Manager on NX-on-GCP / Test Drive.

Author: michael@nutanix.com
Date:   2020-03-05
"""

import sys
import os
import json
import copy
import uuid

sys.path.append(os.path.join(os.getcwd(), "nutest_gcp.egg"))

from framework.lib.nulog import INFO, ERROR
from helpers.rest import RequestResponse
from helpers.calm import (file_to_dict, body_via_v3_get,
                          body_via_v3_post, create_via_v3_post)

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
    bp_spec = file_to_dict("specs/calm_bp_publish.spec")
    INFO(f"bp_spec: {bp_spec}")

    # Get user and icon info
    user_info = body_via_v3_get(pc_external_ip, "users",
                                pc_password, "me").json
    icon_info = body_via_v3_post(pc_external_ip, "app_icons",
                                 pc_password, None).json

    # Loop through the blueprints to upload
    for bp in bp_spec["entities"]:

      # Create our payload and get bp uuid
      payload = {
        "filter": f"name==bp['bp_name']"
      }
      bp_info = body_via_v3_post(pc_external_ip, "blueprints",
                                 pc_password, payload).json
      bp_uuid = bp_info["entities"][0]["metadata"]["uuid"]

      # Get bp spec with uuid
      bp = body_via_v3_get(pc_external_ip, "blueprints",
                           pc_password,
                f"{bp_uuid}/export_json?keep_secrets=true").json

      # Modify our body
      bp["spec"]["name"] = bp_spec["mp_name"]
      bp["status"]["name"] = bp_spec["mp_name"]
      spec = copy.deepcopy(bp["spec"])
      status = copy.deepcopy(bp["status"])
      del bp["spec"]["resources"]
      del bp["status"]
      bp["metadata"]["kind"] = "marketplace_item"
      bp["spec"]["resources"] = {
        "app_attribute_list": ["FEATURED"]
      }
      bp["spec"]["resources"]["app_group_uuid"] = str(uuid.uuid4())
      bp["spec"]["resources"]["author"] = user_info["status"]["name"]
      for icon in icon_info["entities"]:
        if icon["status"]["name"] == bp_spec["icon_name"]:
          bp["spec"]["resources"]["icon_reference_list"].append(
            {
              "icon_reference": {
                "kind": "file_item",
                "uuid": icon["metadata"]["uuid"]
              }
            }
          )
      bp["spec"]["resources"]["version"] = bp_spec["bp_version"]
      bp["spec"]["resources"]["app_blueprint_template"] = {
        "spec": spec
      }
      bp["spec"]["resources"]["app_blueprint_template"]["status"] =\
                status

      # Upload our marketplace item
      resp = create_via_v3_post(pc_external_ip, "calm_marketplace_items",
                                pc_password, bp)

      # Log appropriately based on response
      if (resp.code == 200 or resp.code == 202):
        INFO(f"{bp['bp_name']} blueprint created successfully.")
      else:
        raise Exception(f"{bp['bp_name']} blueprint create" +
                        f" failed with:\n" +
                        f"Error Code: {resp.code}\n" +
                        f"Error Message: {resp.message}")

  except Exception as ex:
    INFO(ex)

if __name__ == '__main__':
  main()

