#!/usr/bin/env bash

# BASE_DIR should point to the root data directory on your system
# (originally /oak/stanford/groups/euan/projects on the Stanford Sherlock cluster).
BASE_DIR="."

bcftools annotate \
  -a "${BASE_DIR}/shriya/vcf/00-All.vcf.gz" \
  -c ID \
  -o mygwas_annotated.vcf.gz \
  -O z \
  "${BASE_DIR}/shriya/mygwas.vcf.gz"
