#!/bin/bash

test_files=("conftest.py" "test_cache.py" "test_init.py" "test_main.py" "test_mutation.py" "test_mutmut_config_hooks.py")

mkdir -p coverage_html

for test_file in "${test_files[@]}"; do
  python -m coverage run "tests/$test_file"
  python -m coverage html
  
  folder_name="${test_file%.py}"
  
  mv htmlcov "$folder_name"
  mv "$folder_name" coverage_html/
  
  python -m coverage erase
done
