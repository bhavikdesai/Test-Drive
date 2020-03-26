#!/usr/local/bin/python3
"""
deploy-nx-on-gcp.py: automation to manage NX-on-GCP Test Drive
clusters.  All functions are included within this file so it's
easily distributable.

Instructions:
1. Add the following GCP Service Account into your GCP Project via
   the IAM section, with "Project Editor" permissions.
   69118586847-compute@developer.gserviceaccount.com
2. Find the "MODIFY FOR YOUR ENVIRONMENT" section below, and
   replace the values with your project details.
3. Run the following command to get help outputs on the various
   ways to run the script.
   python3 manage-nx-on-gcp.py help

Author: michael@nutanix.com
Date:   2020-03-12
"""

import sys
import os
import json
import requests
import time
from datetime import datetime


# ================== MODIFY FOR YOUR ENVIRONMENT ==================
metadata = {
    "projects": ["testdrive02"],  # replace with your project name
    "duration": 24,  # replace with your desired number of hours
    "name": time.strftime("%Y-%m-%d %H:%M:%S")  # optionally change
}

service_name = "$MODERN-DC-TESTDRIVE-DEV"
# This is a value given to you by the NX-on-GCP Eng team. Leaving
# it as-is should be fine, however for certain templates it may
# need to be changed.
# =================================================================


# The headers should not need to be modified
headers = {
    "request-type": "SERVICE",
    "request-service-name": service_name
}


# Given a filename, return a dict of the file's contents
def file_to_dict(filename):
    with open(os.path.join(os.getcwd(), filename)) as json_file:
        return json.load(json_file)


# Function to print script usage help
def print_help():
    print("To deploy a cluster, specify a json template file:")
    print("  python3 manage-nx-on-gcp.py path/to/cluster-spec.json\n")
    print("To get all cluster deployment info, specify the request_id " +
          "UUID and append .info:")
    print("  python3 manage-nx-on-gcp.py <request_id-uuid>.info\n")
    print("To get only cluster IP/password info, specify the request_id" +
          "UUID and append .pass:")
    print("  python3 manage-nx-on-gcp.py <request_id-uuid>.pass\n")
    print("To modify a cluster's duration, specify the request_id " +
          "UUID and append .mod:")
    print("  python3 manage-nx-on-gcp.py <request_id-uuid>.mod\n")
    print("To get cluster deployment logs, specify the request_id " +
          "UUID and append .logs:")
    print("  python3 manage-nx-on-gcp.py <request_id-uuid>.logs\n")
    print("To delete a cluster, specify the request_id " +
          "UUID and append .del:")
    print("  python3 manage-nx-on-gcp.py <request_id-uuid>.del\n")
    print("To use your most recently created cluster, use the following" +
          " tail+awk command:")
    print("  python3 manage-nx-on-gcp.py $(tail -1 requests.ids | awk " +
          "{'print $NF'}).info\n")


# Output the cluster info
def info(cluster, detail):

    # Create the URL and make the call
    req_id = cluster.split(".")[0]
    url = f"https://nx-gcp.nutanix.com/api/v1/deployments/requests/{req_id}"
    resp = requests.get(url, headers=headers)

    # Handle a successful call
    if resp.ok:

        # Make sure it wasn't a non-VPN call
        if str(resp.content).startswith("b'<!DOCTYPE html>"):
            sys.exit("Error: You must be on full-tunnel VPN to use this " +
                     "script.")

        # Print the info
        cluster_info = json.loads(resp.content.decode("utf-8"))
        if detail == "short":
            print(json.dumps(cluster_info["data"],
                             indent=4, sort_keys=True))
        elif detail == "pass":
            pc_info = cluster_info["data"]["data"]["allocated_resources"]\
                                  ["tdaas_pc"]
            pe_info = cluster_info["data"]["data"]["allocated_resources"]\
                                  ["tdaas_cluster"]
            print(f'PC Info:\thttps://{pc_info["external_ip"]}:9440\t\t' +
                  f'{pc_info["prism_password"]}\n' +
                  f'PE Info:\thttps://{pe_info["external_ip"]}:9440\t\t' +
                  f'{pe_info["prism_password"]}')
        else:
            print(json.dumps(cluster_info, indent=4, sort_keys=True))

    # Handle failure
    else:
        print("Request failed with the following detail:")
        print(str(resp))


# Create a cluster for a specified file
def create(cluster):

    # Read in the spec file and conver to dict
    cluster_spec = file_to_dict(cluster)

    # Create the payload
    payload = {
        "resource_specs": cluster_spec,
        "metadata": metadata
    }

    # Create the URL and make the call
    url = "https://nx-gcp.nutanix.com/api/v1/deployments/requests"
    resp = requests.post(url, json=payload, headers=headers)

    # Handle success
    if resp.ok:

        # Make sure it wasn't a non-VPN call
        if str(resp.content).startswith("b'<!DOCTYPE html>"):
            sys.exit("Error: You must be on full-tunnel VPN to use this " +
                     "script.")

        # Set the response as a dictionary (return is a byte)
        request_info = json.loads(resp.content.decode("utf-8"))
        print("=== " + request_info["message"] + " ===")

        # Add the request id to the file for usage later
        f = open("requests.ids", "a")
        f.write(
            f"{metadata['name']}:    {request_info['data']['request_id']}\n")
        f.close()
        print("The request_id has been added to your 'requests.ids' file.\n")

        # Call the info function to get additional detail on the deployment
        time.sleep(5)
        info(request_info['data']['request_id'], "short")

    # Handle failure
    else:
        print("Request failed with the following detail:")
        print(json.dumps(json.loads(resp.content.decode("utf-8")),
                         indent=4, sort_keys=True))


# Modify a cluster's duration time
def modify(cluster):

    # Print time and short version of info so user knows current state
    t = datetime.utcnow()
    print("Current time (UTC) " + str(t))
    req_id = cluster.split(".")[0]
    info(req_id, "short")

    # Get users input for how long to extend the cluster
    while True:
        try:
            hours = int(
                input(f"Enter the number of hours to extend request: "))
            if hours > 720 or hours < 1:
                print("Please enter in a number between 1 and 720, inclusive.")
                continue
            break
        except ValueError:
            print("Please enter in a valid number.")
            continue

    # Create the payload
    payload = {
        "duration": hours
    }

    # Create the URL and make the call
    url = f"https://nx-gcp.nutanix.com/api/v1/deployments/requests/{req_id}" +\
        "/modify_duration"
    resp = requests.post(url, json=payload, headers=headers)

    # Handle success or failure
    if resp.ok:
        extend_info = json.loads(resp.content.decode("utf-8"))
        print("=== " + extend_info["message"] + " ===")
        info(req_id, "short")

    else:
        print("Request failed with the following detail:")
        print(str(resp))


# Downloads logs of a cluster
def logs(cluster):

    # Create the URL and make the call
    req_id = cluster.split(".")[0]
    url = f"https://nx-gcp.nutanix.com/api/v1/deployments/requests/{req_id}" +\
          f"/plugins/logs"
    resp = requests.get(url, allow_redirects=True, headers=headers)

    # Download the file if successful
    if resp.ok:
        open(f"{req_id}-logs.zip", "wb").write(resp.content)
        print("=== Successfully downloaded file ===")
        print(f"{req_id}-logs.zip")

    # Error out if not
    else:
        print("Request failed with the following detail:")
        print(str(resp))


# Delete a cluster
def delete(cluster):

    # Print cluster info
    req_id = cluster.split(".")[0]
    info(req_id, "short")

    # Make sure the user really wants to delete the cluster
    while True:
        yesno = input("Are you sure you want to delete this cluster?" +
                      " [y]es/[n]o: ")
        if yesno.lower() == "n" or yesno.lower() == "no":
            print("Deletion cancelled. Exiting.")
            return
        elif yesno.lower() != "y" and yesno.lower() != "yes":
            print("Please enter either [y]es or [n]o.")
            continue
        break

    # Create the URL and make the call
    url = f"https://nx-gcp.nutanix.com/api/v1/deployments/requests/{req_id}" +\
        "/release"
    resp = requests.post(url, headers=headers)

    # Handle success or failure
    if resp.ok:
        delete_info = json.loads(resp.content.decode("utf-8"))
        print("=== " + delete_info["message"] + " ===")
        info(req_id, "short")

    else:
        print("Request failed with the following detail:")
        print(str(resp))


# Main function, handle inputs and call correct functions
if __name__ == '__main__':

    # Error out if no spec file was passed via CLI
    if len(sys.argv) == 1:
        print("Error: please specify at least one argument when running " +
              "this script.  Examples:\n")
        print_help()

    # Print script info if "help" is passed
    elif sys.argv[1].lower().endswith("help") or\
            sys.argv[1].lower() == "-h":
        print("Use this script to deploy, manage, and reclaim NX-on-GCP " +
              "clusters.\n")
        print_help()

    # Create an NX-on-GCP cluster for each cluster spec file
    else:
        for cluster in sys.argv:
            if not cluster.endswith("py"):
                # Create a cluster
                if cluster.endswith("json"):
                    create(cluster)
                # Get info on a cluster
                elif cluster.endswith("info"):
                    info(cluster, "long")
                elif cluster.endswith("pass"):
                    info(cluster, "pass")
                # Download logs for a cluster
                elif cluster.endswith("logs"):
                    logs(cluster)
                # Extend a cluster's duration
                elif cluster.endswith("mod"):
                    modify(cluster)
                # Delete a cluster
                elif cluster.endswith("del"):
                    delete(cluster)
                else:
                    print("Error: you did not specify a valid argument.\n")
                    print_help()
