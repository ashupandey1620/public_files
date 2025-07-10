# analysis/graph_builder.py

import os
import re
import networkx as nx

# This function extracts all procedure names from a PL/I file
def extract_procedures_from_file(filepath):
    procedures = []
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
        # Match things like PROC_NAME: PROC
        matches = re.findall(r'(?im)^\s*(\w+):\s*PROC', content)
        procedures.extend(matches)
    return procedures

# This function finds all CALL statements in a file
# and maps them from a specific procedure
def extract_calls_from_procedure(proc_body):
    return re.findall(r'(?i)CALL\s+(\w+)\s*;', proc_body)

def extract_procedures_and_calls(filepath):
    proc_map = {}  # {proc_name: [called_procs]}
    current_proc = None
    body_lines = []

    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            match = re.match(r'(?i)^\s*(\w+):\s*PROC', line)
            if match:
                if current_proc and body_lines:
                    body = "\n".join(body_lines)
                    proc_map[current_proc] = extract_calls_from_procedure(body)
                current_proc = match.group(1)
                body_lines = []
            elif current_proc:
                body_lines.append(line)

        if current_proc and body_lines:
            body = "\n".join(body_lines)
            proc_map[current_proc] = extract_calls_from_procedure(body)

    return proc_map

def build_dependency_graph(files):
    G = nx.DiGraph()
    proc_to_file = {}

    # First pass: create all nodes and map procedures to files
    for file in files:
        proc_map = extract_procedures_and_calls(file)
        for proc in proc_map:
            G.add_node(proc)
            proc_to_file[proc] = file

    # Second pass: create edges for CALLs
    for file in files:
        proc_map = extract_procedures_and_calls(file)
        for proc, calls in proc_map.items():
            for callee in calls:
                G.add_edge(proc, callee)

    return G, proc_to_file
