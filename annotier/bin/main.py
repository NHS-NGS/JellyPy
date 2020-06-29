import json
import os
import sqlite3

from sample_analysis import find_json, get_json_data, run_analysis


# main functions to run analysis for list of samples and generate report

samples=[
    "871-1",
    "981-1",
    "982-1",
    "26181-1",
    "44543-1",
    "55904-1"
    ]

for i in samples:
    ir_json = find_json(i)
    hpo_terms, variant_list, position_list = get_json_data(ir_json)
    run_analysis(position_list)
