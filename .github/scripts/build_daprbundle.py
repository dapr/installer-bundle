# ------------------------------------------------------------
# Copyright 2021 The Dapr Authors
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ------------------------------------------------------------


import argparse
from errno import ESTALE
from fileinput import filename
from http.client import OK
import subprocess
import tarfile
from tkinter import Variable
import zipfile
import requests
import json
import os
import sys
import shutil
import semver
import stat


# GitHub Organization and repo name to download release
GITHUB_ORG="dapr"
GITHUB_DAPR_REPO="dapr"
GITHUB_DASHBOARD_REPO="dashboard"
GITHUB_CLI_REPO="cli"

# Dapr binaries filename
DAPRD_FILENAME="daprd"
PLACEMENT_FILENAME="placement"
DASHBOARD_FILENAME="dashboard"
CLI_FILENAME="dapr"
DAPRBUNDLE_FILENAME="daprbundle"

BIN_DIR="dist"
IMAGE_DIR="docker"
BUNDLE_DIR="daprbundle"
ARCHIVE_DIR="archive"

DAPR_IMAGE="daprio/dapr"
detailsFileName="details.json"


global runtime_os,runtime_arch,runtime_ver,dashboard_ver,cli_ver


# Returns latest release/pre-release version of the given repo from GitHub (e.g. `dapr`)
def getLatestRelease(repo):
    daprReleaseUrl = "https://api.github.com/repos/" + GITHUB_ORG + "/" + repo + "/releases"
    print(daprReleaseUrl)
    resp = requests.get(daprReleaseUrl)
    if resp.status_code != requests.codes.ok:
        print(f"Error pulling latest release of {repo}")
        resp.raise_for_status()
        sys.exit(1)
    data = json.loads(resp.text)
    versions = []
    for release in data:
        if not release["draft"]:
            versions.append(release["tag_name"].lstrip("v"))
    if len(versions) == 0:
        print(f"No releases found for {repo}")
        sys.exit(1)
    latest_release = versions[0]
    for version in versions:
        if semver.compare(version,latest_release) > 0:
            latest_release = version
    return latest_release

# Returns the complete filename of the archived binary(e.g. `daprd_linux_amd64.tar.gz`)
def binaryFileName(fileBase):
    if(runtime_os == "windows"):
        ext = "zip"
    else:
        ext = "tar.gz"
    fileName = f"{fileBase}_{runtime_os}_{runtime_arch}.{ext}"
    return fileName

# Creates archive file of the binary in `src` folder and places it in `dest` folder
def make_archive(src,dest,fileBase):
    print(f"Archiving {src} to {os.path.join(dest,binaryFileName(fileBase))}")
    fileNameBase = f"{fileBase}_{runtime_os}_{runtime_arch}"
    filePathBase = os.path.join(dest,fileNameBase)
    if runtime_os == "windows":
        shutil.make_archive(filePathBase,"zip",".",src)
    else:
        shutil.make_archive(filePathBase,"gztar",".",src)

# Extracts the given archived file in `dir` folder
def unpack_archive(filePath,dir):
    print(f"Extracting {filePath} to {dir}")
    if filePath.endswith('.zip'):
        shutil.unpack_archive(filePath,dir,"zip")
    else:
        if filePath.endswith('.tar.gz'):
            shutil.unpack_archive(filePath,dir,"gztar")
        else:
            print(f"Unknown archive file {filePath}")
            sys.exit(1)

# Downloads the given  dapr binary(e.g. `daprd`) from the github `repo` and places it in `out_dir` folder
def downloadBinary(repo, fileBase, version, out_dir):
    fileName = binaryFileName(fileBase)
    url = f"https://github.com/{GITHUB_ORG}/{repo}/releases/download/v{version}/{fileName}"
    downloadPath = os.path.join(out_dir,fileName)

    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    print(f"Downloading {url} to {downloadPath}")

    resp = requests.get(url,stream=True)
    if resp.status_code == 200:
        with open(downloadPath, 'wb') as f:
            f.write(resp.raw.read())
    else:
        print(f"Error: Unable to Download {url}")

    print(f"Downloaded {url} to {downloadPath}")

# Downloads all required dapr binaries (`daprd`,`placement`,`dashboard`) in `BIN_DIR` subfolder and dapr cli (`dapr`) in `dir` folder
def downloadBinaries(dir):
    bin_dir = os.path.join(dir,BIN_DIR)
    downloadBinary(GITHUB_DAPR_REPO,DAPRD_FILENAME,runtime_ver,bin_dir)
    downloadBinary(GITHUB_DAPR_REPO,PLACEMENT_FILENAME,runtime_ver,bin_dir)
    downloadBinary(GITHUB_DASHBOARD_REPO,DASHBOARD_FILENAME,dashboard_ver,bin_dir)
    downloadBinary(GITHUB_CLI_REPO,CLI_FILENAME,cli_ver,dir)

    cli_filepath = os.path.join(dir,binaryFileName(CLI_FILENAME))
    unpack_archive(cli_filepath,dir)
    os.remove(cli_filepath)

# Returns the fileName of the docker image to be saved.
# E.g., for image `daprio/dapr:1.7.0`, the fileName would be `daprio-dapr-1.7.0.tar.gz`
def getFileName(image):
    fileName = image.replace("/","-").replace(":","-") + ".tar.gz"
    return fileName

# Downloads the givern version of docker image and saves it in `out_dir` folder
def downloadDockerImage(image_name, version, out_dir):
    docker_image=f"{image_name}:{version}"
    if (version == "latest"):
        docker_image =image_name
    fileName = getFileName(docker_image)
    downloadPath = os.path.join(out_dir,fileName)

    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    print(f"Downloading {docker_image} to {downloadPath}")

    cmd = ["docker", "pull",docker_image]
    completed_process = subprocess.run(cmd,text=True)
    if(completed_process.returncode != 0):
        print(f"Error pulling docker image {docker_image}")
        sys.exit(1)
    
    cmd = ["docker", "save", "-o", downloadPath, docker_image]
    completed_process = subprocess.run(cmd,text=True)
    if(completed_process.returncode != 0):
        print(f"Error saving docker image {docker_image}")
        sys.exit(1)

    print(f"Downloaded {docker_image} to {downloadPath}")

# Downloads all required docker images and saves it in `IMAGE_DIR` subfolder of `dir`
def downloadDockerImages(dir):
    image_dir = os.path.join(dir,IMAGE_DIR)
    downloadDockerImage(DAPR_IMAGE,runtime_ver,image_dir)

# Parses command line arguments
def parseArguments():
    global runtime_os,runtime_arch,runtime_ver,dashboard_ver,cli_ver,ARCHIVE_DIR
    all_args = argparse.ArgumentParser()
    all_args.add_argument("--runtime_os",required=True,help="Runtime OS: [windows/linux/darwin]")
    all_args.add_argument("--runtime_arch",required=True,help="Runtime Architecture: [amd64/arm/arm64]")
    all_args.add_argument("--runtime_ver",default="latest",help="Dapr Runtime Version: default=latest e.g. 1.6.0")
    all_args.add_argument("--dashboard_ver",default="latest",help="Dapr Dashboard Version: default=latest e.g. 0.9.0")
    all_args.add_argument("--cli_ver",default="latest",help="Dapr CLI Version: default=latest e.g. 1.6.0")
    all_args.add_argument("--archive_dir",default="archive",help="Output Archive directory: default=archive")

    args = vars(all_args.parse_args())
    runtime_os = str(args['runtime_os'])
    runtime_arch = str(args['runtime_arch'])
    runtime_ver = str(args["runtime_ver"])
    dashboard_ver = str(args["dashboard_ver"])
    cli_ver = str(args["cli_ver"])
    ARCHIVE_DIR = str(args["archive_dir"])

    if runtime_ver == "latest" or runtime_ver == "":
        runtime_ver = getLatestRelease(GITHUB_DAPR_REPO)
    if dashboard_ver == "latest" or dashboard_ver == "":
        dashboard_ver = getLatestRelease(GITHUB_DASHBOARD_REPO)
    if cli_ver == "latest" or cli_ver == "":
        cli_ver = getLatestRelease(GITHUB_CLI_REPO)

# Deletes a file if exists
def deleteIfExists(dir):
    if os.path.exists(dir):
        if os.path.isdir(dir):
            shutil.rmtree(dir)
        else:
            os.remove(dir)

# Writes details about versions, sub-folders, and images in `details.json`
def write_details(dir):
    daprImageName = f"{DAPR_IMAGE}:{runtime_ver}"
    daprImageFileName = getFileName(daprImageName)
    details = {
        "daprd" : runtime_ver,
        "dashboard": dashboard_ver,
        "cli": cli_ver,
        "daprBinarySubDir": BIN_DIR,
        "dockerImageSubDir": IMAGE_DIR,
        "daprImageName": daprImageName,
        "daprImageFileName": daprImageFileName
    }
    jsonString = json.dumps(details)
    filePath = os.path.join(dir,detailsFileName)
    with open(filePath,'w') as f:
        f.write(jsonString)
    os.chmod(filePath, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
    print(f"File {detailsFileName} is set to Read-Only")


#############Main###################

#Parsing Arguments
parseArguments()

#Cleaning the bundle and archive  directory
deleteIfExists(BUNDLE_DIR)
deleteIfExists(ARCHIVE_DIR)

out_dir = BUNDLE_DIR
#Downloading Binaries
downloadBinaries(out_dir)

#Downloading Docker images
downloadDockerImages(out_dir)

#writing versions
write_details(out_dir)

#Archiving bundle
make_archive(BUNDLE_DIR,ARCHIVE_DIR,DAPRBUNDLE_FILENAME)
