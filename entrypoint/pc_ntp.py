"""
pc_authconfig.py: automation to configure NTP
on NX-on-GCP / Test Drive.

Author: michael@nutanix.com
Date:   2020-03-30
"""

import sys
import os
import json

sys.path.append(os.path.join(os.getcwd(), "nutest_gcp.egg"))

from framework.lib.nulog import INFO, ERROR
from helpers.rest import RequestResponse
from helpers.calm import (file_to_dict, create_via_v1_post)


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

    # Read in our spec file
    ntp_spec = file_to_dict("specs/pc_ntp.spec")
    INFO(f"ntp_spec: {ntp_spec}")

    # Make API call to configure the authconfig
    resp = create_via_v1_post(pc_external_ip,
                              "cluster/ntp_servers/add_list",
                              pc_password, ntp_spec["entities"])

    # Log appropriately based on response
    if (resp.code == 200 or resp.code == 202):
      INFO("NTP configured successfully.")
    else:
      raise Exception(f"NTP config failed with:\n" +
                      f"Error Code: {resp.code}\n" +
                      f"Error Message: {resp.message}")

  except Exception as ex:
    INFO(ex)

if __name__ == '__main__':
  main()
