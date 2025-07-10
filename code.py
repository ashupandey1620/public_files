# analysis/graph_viz.py

from pyvis.network import Network
import networkx as nx
import tempfile
import os
import streamlit.components.v1 as components
import streamlit as st

def visualize_graph(graph: nx.DiGraph, changed: list, impacted: list, enable_download: bool = False, proc_to_file: dict = None):
    net = Network(height='600px', width='100%', directed=True, notebook=False)
    added_files = set()

    file_clusters = {}

    for node in graph.nodes():
        # Map procedure to actual file
        if proc_to_file and node in proc_to_file:
            file_node = os.path.basename(proc_to_file[node])
        else:
            file_node = node.split('_')[0] + ".pli"

        # Add file node once
        if file_node not in added_files:
            net.add_node(file_node, label=file_node, color="#90ee90", shape="box", group=file_node)
            added_files.add(file_node)

        # Determine color of procedure node
        if node in changed:
            if node in impacted:
                color = "#ffa500"  # Orange for impacted changed
            else:
                color = "#ff4b4b"  # Red for changed
        elif node in impacted:
            color = "#ffa500"  # Orange for impacted
        else:
            color = "#97c2fc"  # Blue for normal

        # Grouping procedures under their file
        net.add_node(node, label=node, color=color, group=file_node)
        net.add_edge(file_node, node)

    for source, target in graph.edges():
        net.add_edge(source, target)

    temp_dir = tempfile.mkdtemp()
    output_path = os.path.join(temp_dir, "graph.html")
    net.save_graph(output_path)

    with open(output_path, 'r', encoding='utf-8') as f:
        html = f.read()
        components.html(html, height=650, scrolling=True)

    with st.expander("🟢 Color Legend"):
        st.markdown("""
        - 🟩 **Green**: PL/I Source File (container box)
        - 🔵 **Blue**: Unchanged procedure
        - 🟠 **Orange**: Impacted procedure
        - 🔴 **Red**: Changed procedure
        """)

    if enable_download:
        with open(output_path, 'rb') as f:
            st.download_button(
                label="Download Graph Visualization (HTML)",
                data=f,
                file_name="dependency_graph.html",
                mime="text/html"
            )
