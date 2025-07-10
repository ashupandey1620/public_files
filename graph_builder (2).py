# app.py
import os
import json
import requests
import streamlit as st
import networkx as nx
import pandas as pd
from agents.change_agent import detect_changes
from agents.impact_agent import analyze_impact
from agents.regression_agent import suggest_tests
from analysis.parser import get_pl1_files
from analysis.graph_builder import build_dependency_graph
from analysis.diff_utils import generate_diff
from analysis.graph_viz import visualize_graph



def analyze_impact_with_llm(change_code, target_code, change_file, target_file):
    headers = {
        "Content-Type": "application/json",
        "api-key": API_KEY
    }

    prompt = f"""
You are a PL/I code analysis expert.

A change has been made in the following file ({change_file}):

--- Changed Code Start ---
{change_code}
--- Changed Code End ---

Below is the content of a potentially affected file ({target_file}):

--- Target File Start ---
{target_code}
--- Target File End ---

Based on the change, does this affect the logic, data flow, or behavior in {target_file}? If yes, where and why? Reply briefly.
"""

    data = {
        "messages": [
            {"role": "system", "content": "You are a helpful assistant for code impact analysis."},
            {"role": "user", "content": prompt}
        ]
    }

    try:
        response = requests.post(ENDPOINT, headers=headers, data=json.dumps(data))
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"].strip()
        else:
            return f"Error {response.status_code}: {response.text}"
    except Exception as e:
        return f"Request failed: {e}"

st.title("PL/I Code Impact Analysis Tool")

old_folder = st.text_input("Path to OLD version of code")
new_folder = st.text_input("Path to NEW version of code")

if st.button("Run Impact Analysis"):
    if not os.path.isdir(old_folder) or not os.path.isdir(new_folder):
        st.error("Please enter valid folder paths")
    else:
        st.info("Processing...")

        old_files = get_pl1_files(old_folder)
        new_files = get_pl1_files(new_folder)

        old_map = {os.path.basename(f): f for f in old_files}
        new_map = {os.path.basename(f): f for f in new_files}

        changed_files = detect_changes(old_map, new_map)

        all_files_old = list(set(old_files))
        all_files_new = list(set(new_files))

        graph_old, proc_file_map_old = build_dependency_graph(all_files_old)
        graph_new, proc_file_map_new = build_dependency_graph(all_files_new)

        st.subheader("📌 Dependency Graph - OLD Version")
        visualize_graph(graph_old, [], [], proc_to_file=proc_file_map_old)

        st.subheader("📌 Dependency Graph - NEW Version")
        visualize_graph(graph_new, [], [], proc_to_file=proc_file_map_new)

        if not changed_files:
            st.success("No differences found between files.")
        else:
            st.write(f"Changed files: {changed_files}")

            changed_procs = [os.path.splitext(f)[0] for f in changed_files]
            all_affected_procs = set(changed_procs)

            impact_map = {}  # {changed_file: [impacted_file, ...]}

            for proc_name, changed_file in zip(changed_procs, changed_files):
                if proc_name in graph_new:
                    upstream = nx.ancestors(graph_new, proc_name)
                    impact_map[changed_file] = [f + ".pli" for f in upstream]
                    impacted = list(upstream)  # maintain use of impacted variable for tests, diff, display
                else:
                    impact_map[changed_file] = []
                    impacted = []

                st.subheader(f"Impacted by {proc_name}:")
                st.write(impacted)

                tests = suggest_tests(impacted)
                st.markdown("**Suggested Regression Tests:**")
                st.write(tests)

                try:
                    with open(old_map[changed_file], 'r', encoding='utf-8', errors='ignore') as f1, \
                         open(new_map[changed_file], 'r', encoding='utf-8', errors='ignore') as f2:
                        old_code = f1.read()
                        new_code = f2.read()
                        diff = generate_diff(old_code, new_code)

                    results = {}
                    results[proc_name] = {
                        "impacted": impacted,
                        "tests": tests,
                        "diff": diff
                    }

                except Exception as e:
                    st.warning(f"Error processing {changed_file}: {e}")

            st.markdown("### 🔍 Full Impact Map")
            for k, v in impact_map.items():
                st.text(f"{k} ➝ {v}")

            llm_results = []
            for changed_file, impacted_files in impact_map.items():
                if changed_file in new_map:
                    try:
                        with open(new_map[changed_file], 'r', encoding='utf-8', errors='ignore') as f:
                            changed_code = f.read()

                        for impacted_file in impacted_files:
                            if impacted_file in new_map:
                                with open(new_map[impacted_file], 'r', encoding='utf-8', errors='ignore') as f:
                                    impacted_code = f.read()
                                st.write(f"🔍 Calling GPT for impact check: {changed_file} ➝ {impacted_file}")
                                explanation = analyze_impact_with_llm(changed_code, impacted_code, changed_file, impacted_file)
                                st.write(f"✅ LLM Response: {explanation[:100]}...")
                                llm_results.append({
                                    "Changed File": changed_file,
                                    "Impacted File": impacted_file,
                                    "LLM Review": explanation
                                })
                    except Exception as e:
                        st.warning(f"LLM impact check failed for {changed_file}: {e}")

            st.subheader("📌 Highlighted Dependency Graph (NEW)")
            visualize_graph(graph_new, list(all_affected_procs), [], proc_to_file=proc_file_map_new)

            if llm_results:
                df = pd.DataFrame(llm_results)
                st.dataframe(df)
                st.download_button(
                    label="Download LLM Impact Review (Excel)",
                    data=df.to_excel(index=False, engine='openpyxl'),
                    file_name="llm_impact_review.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
