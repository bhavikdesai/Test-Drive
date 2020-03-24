#!/bin/bash

BUCKET=$(git branch | grep \* | awk '{print $NF}')
echo "Taring up directory:"
tar -zcvf entrypoint.tar.gz entrypoint
echo "Copying to GCP bucket $BUCKET"
gsutil cp entrypoint.tar.gz gs://testdrive-templates/library/$BUCKET/entrypoint.tar.gz
echo "Removing tarball"
rm entrypoint.tar.gz
