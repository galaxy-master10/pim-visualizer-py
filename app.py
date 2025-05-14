import streamlit as st
from sqlalchemy import create_engine, MetaData, inspect, Table, text
import networkx as nx
from pyvis.network import Network
import tempfile
import pandas as pd
from collections import defaultdict

# First Streamlit command must be set_page_config
st.set_page_config(layout="wide")
st.title("🔍 Advanced ERD Explorer")

# 1) Get connection string
conn_str = st.text_input(
    "Enter your DB connection string (SQLAlchemy URI)",
    value="mssql+pyodbc://SA:%23said8500@localhost:1433/Digit.Pim?driver=ODBC+Driver+17+for+SQL+Server&TrustServerCertificate=yes"
)
if not conn_str:
    st.warning("▶️ Please paste your connection string above and press Enter.")
    st.stop()

# 2) Test connection and reflect metadata
try:
    engine = create_engine(conn_str)
    # Test connection
    engine.connect()
    st.success("✅ Connection OK!")
    
    # Reflect all tables
    metadata = MetaData()
    metadata.reflect(bind=engine)
    inspector = inspect(engine)
    
except Exception as e:
    st.error(f"❌ Connection or reflection failed:\n```\n{e}\n```")
    st.stop()

# 3) Build the directed graph of FKs with additional information
G = nx.DiGraph()
table_fk_counts = defaultdict(int)
table_cols_count = {}
table_relations = defaultdict(list)

# Gather all table and relationship information
for tbl in metadata.sorted_tables:
    table_name = tbl.name
    G.add_node(table_name)
    
    # Count columns
    table_cols_count[table_name] = len(tbl.columns)
    
    # Add foreign keys
    for fk in tbl.foreign_keys:
        parent = fk.column.table.name
        child = table_name
        fk_column = fk.parent.name
        ref_column = fk.column.name
        
        # Store relationship info
        table_fk_counts[parent] += 1
        table_fk_counts[child] += 1
        
        relation_info = {
            "parent": parent,
            "child": child,
            "fk_column": fk_column,
            "ref_column": ref_column
        }
        table_relations[parent].append(relation_info)
        table_relations[child].append(relation_info)
        
        G.add_edge(parent, child, fk_column=fk_column, ref_column=ref_column)

# 4) Dashboard tabs
tab1, tab2, tab3 = st.tabs(["ERD Explorer", "Schema Analysis", "Relationship Path Finder"])

with tab1:
    # Sidebar controls
    st.sidebar.header("🔧 Controls")
    
    # Table selection dropdown
    table_list = ["All"] + sorted(G.nodes())
    selected = st.sidebar.selectbox("Focus on table", table_list)
    
    # Visualization options
    st.sidebar.subheader("Visualization Options")
    show_labels = st.sidebar.checkbox("Show edge labels", value=False)
    node_size_by = st.sidebar.radio(
        "Node size based on:",
        ["Connections", "Columns", "Equal Size"]
    )
    
    # Extract subgraph if needed
    if selected != "All":
        # Include direct relationships (1-degree)
        neighbors = set(G.predecessors(selected)) | set(G.successors(selected))
        sub_nodes = {selected} | neighbors
        
        # Option to include 2nd degree relationships
        if st.sidebar.checkbox("Include 2nd-degree relationships", value=False):
            second_degree = set()
            for node in neighbors:
                second_degree |= set(G.predecessors(node)) | set(G.successors(node))
            sub_nodes |= second_degree
            
        subG = G.subgraph(sub_nodes).copy()
    else:
        subG = G

    # Render with PyVis
    net = Network(height="600px", width="100%", directed=True)
    
    # Node sizes based on selection
    for n in subG.nodes():
        size = 25  # Default size
        
        if node_size_by == "Connections":
            size = 15 + table_fk_counts[n]
        elif node_size_by == "Columns":
            size = 15 + table_cols_count[n] * 0.5
        
        # Set node colors: highlighted table is red, others are blue
        color = "#3498db"  # Default blue
        if selected != "All" and n == selected:
            color = "#e74c3c"  # Highlight selected in red
        
        net.add_node(n, label=n, title=f"Table: {n}\nColumns: {table_cols_count[n]}\nConnections: {table_fk_counts[n]}", 
                     size=size, color=color)
    
    # Add edges with optional labels
    for u, v, d in subG.edges(data=True):
        label = ""
        if show_labels:
            label = f"{d.get('fk_column', '?')} -> {d.get('ref_column', '?')}"
        net.add_edge(u, v, title=f"{d.get('fk_column', '?')} -> {d.get('ref_column', '?')}", label=label)

    # Add physics options for better layout
    net.set_options("""
    {
      "physics": {
        "forceAtlas2Based": {
          "gravitationalConstant": -50,
          "centralGravity": 0.01,
          "springLength": 100,
          "springConstant": 0.08
        },
        "maxVelocity": 50,
        "solver": "forceAtlas2Based",
        "timestep": 0.35,
        "stabilization": {
          "enabled": true,
          "iterations": 1000
        }
      }
    }
    """)
    
    tmp = tempfile.NamedTemporaryFile(suffix=".html", delete=False)
    net.save_graph(tmp.name)
    html = open(tmp.name, 'r', encoding='utf-8').read()
    st.components.v1.html(html, height=600)
    
    # 5) Table Details Section - Enhanced
    if selected != "All":
        st.markdown(f"## 📋 Table Details: `{selected}`")
        
        # Basic stats
        col1, col2, col3 = st.columns(3)
        col1.metric("Columns", table_cols_count[selected])
        col2.metric("Incoming Relations", len(list(G.predecessors(selected))))
        col3.metric("Outgoing Relations", len(list(G.successors(selected))))
        
        # Column information with enhanced details
        st.subheader("Columns")
        cols = inspector.get_columns(selected)
        
        col_data = []
        for i, c in enumerate(cols):
            col_info = {
                "name": c["name"],
                "type": str(c["type"]),
                "nullable": c["nullable"],
                "default": c.get("default", "—"),
                "autoincrement": c.get("autoincrement", False),
                "comment": c.get("comment", "—")
            }
            col_data.append(col_info)
        
        st.table(pd.DataFrame(col_data))
        
        # Primary Keys
        st.subheader("Primary Key")
        pk = inspector.get_pk_constraint(selected).get("constrained_columns", [])
        st.write(pk or "— no PK defined —")

        # Foreign Keys - Enhanced with visual indicators
        st.subheader("Foreign Keys")
        fks = inspector.get_foreign_keys(selected)
        
        if fks:
            fk_data = []
            for fk in fks:
                fk_info = {
                    "column": ", ".join(fk["constrained_columns"]),
                    "references": f"{fk['referred_table']}.{', '.join(fk['referred_columns'])}",
                    "name": fk.get("name", "—")
                }
                fk_data.append(fk_info)
            
            st.table(pd.DataFrame(fk_data))
        else:
            st.write("— no FKs —")
            
        # Tables that reference this table
        st.subheader("Referenced by")
        referencing_tables = list(G.predecessors(selected))
        
        if referencing_tables:
            ref_data = []
            for ref_table in referencing_tables:
                for e in G.edges([ref_table, selected], data=True):
                    if e[1] == selected:  # This table is referenced
                        ref_info = {
                            "table": e[0],
                            "column": e[2].get("fk_column", "—"),
                            "references": f"{selected}.{e[2].get('ref_column', '—')}"
                        }
                        ref_data.append(ref_info)
            
            st.table(pd.DataFrame(ref_data))
        else:
            st.write("— no tables reference this table —")

        # Sample data preview (if available)
        st.subheader("Sample Data")
        try:
            with engine.connect() as conn:
                query = text(f"SELECT TOP 5 * FROM [{selected}]")
                result = conn.execute(query)
                df = pd.DataFrame(result.fetchall(), columns=result.keys())
                if not df.empty:
                    st.dataframe(df)
                else:
                    st.write("— no data available —")
        except Exception as e:
            st.write(f"— error retrieving sample data: {str(e)} —")
            
with tab2:
    st.header("Schema Analysis")
    
    # Database Statistics
    st.subheader("Database Overview")
    
    # Stats calculation
    total_tables = len(G.nodes())
    total_relationships = len(G.edges())
    isolated_tables = [n for n in G.nodes() if G.degree(n) == 0]
    most_connected = sorted(G.nodes(), key=lambda x: G.degree(x), reverse=True)[:5]
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Tables", total_tables)
    col2.metric("Relationships", total_relationships)
    col3.metric("Isolated Tables", len(isolated_tables))
    col4.metric("Connectivity Ratio", round(total_relationships/total_tables, 2) if total_tables > 0 else 0)
    
    # Schema patterns section
    st.subheader("Schema Patterns")
    
    # Find join/bridge tables (tables with 2+ FKs and few other columns)
    join_tables = []
    for tbl in metadata.sorted_tables:
        fk_count = len([fk for fk in tbl.foreign_keys])
        non_fk_columns = len(tbl.columns) - fk_count
        if fk_count >= 2 and non_fk_columns <= 2:
            join_tables.append({"table": tbl.name, "fk_count": fk_count, "other_columns": non_fk_columns})
    
    # Display join tables
    if join_tables:
        st.write("🔀 Detected Join/Bridge Tables:")
        st.table(pd.DataFrame(join_tables))
    
    # Identify tables with high fan-out (many outgoing relationships)
    fanout_tables = [(n, G.out_degree(n)) for n in G.nodes() if G.out_degree(n) > 2]
    if fanout_tables:
        st.write("🌟 Tables with High Fan-out (many outgoing relationships):")
        st.table(pd.DataFrame(fanout_tables, columns=["Table", "Outgoing Relationships"]))
    
    # Identify tables with high fan-in (many incoming relationships)
    fanin_tables = [(n, G.in_degree(n)) for n in G.nodes() if G.in_degree(n) > 2]
    if fanin_tables:
        st.write("🎯 Tables with High Fan-in (many incoming relationships):")
        st.table(pd.DataFrame(fanin_tables, columns=["Table", "Incoming Relationships"]))
    
    # Most connected tables
    st.subheader("Most Connected Tables")
    most_connected_data = [(n, G.degree(n)) for n in most_connected]
    st.table(pd.DataFrame(most_connected_data, columns=["Table", "Total Connections"]))
    
    # Isolated tables
    if isolated_tables:
        st.subheader("Isolated Tables (no relationships)")
        st.write(", ".join(isolated_tables))
    
    # Table naming patterns
    st.subheader("Table Naming Patterns")
    
    # Find common prefixes/suffixes
    prefixes = defaultdict(list)
    for tbl in G.nodes():
        parts = tbl.split('_')
        if len(parts) > 1:
            prefix = parts[0]
            prefixes[prefix].append(tbl)
    
    # Display naming patterns
    if prefixes:
        st.write("Detected Table Groupings by Prefix:")
        for prefix, tables in sorted(prefixes.items(), key=lambda x: len(x[1]), reverse=True):
            if len(tables) > 1:
                st.write(f"**{prefix}_** ({len(tables)} tables)")
                st.write(", ".join(tables[:5]) + ("..." if len(tables) > 5 else ""))

with tab3:
    st.header("Relationship Path Finder")
    
    col1, col2 = st.columns(2)
    with col1:
        source_table = st.selectbox("Source Table", sorted(G.nodes()), key="source")
    with col2:
        target_table = st.selectbox("Target Table", sorted(G.nodes()), key="target")
    
    if st.button("Find Relationship Paths"):
        if source_table == target_table:
            st.warning("Source and target tables are the same")
        else:
            try:
                # Find all paths between source and target
                all_paths = list(nx.all_simple_paths(G, source=source_table, target=target_table, cutoff=4))
                
                if all_paths:
                    st.success(f"Found {len(all_paths)} path(s) from {source_table} to {target_table}")
                    
                    for i, path in enumerate(all_paths[:5]):  # Limit to 5 paths
                        st.subheader(f"Path {i+1} ({len(path)-1} hops)")
                        
                        # Create a visualization of this path
                        path_G = nx.DiGraph()
                        for j in range(len(path)-1):
                            src, dst = path[j], path[j+1]
                            edge_data = next((d for u, v, d in G.edges(data=True) 
                                           if u == src and v == dst), {})
                            path_G.add_edge(src, dst, **edge_data)
                        
                        # Render path diagram
                        net = Network(height="200px", width="100%", directed=True)
                        for n in path_G.nodes():
                            color = "#3498db"  # Default blue
                            if n == source_table:
                                color = "#2ecc71"  # Green for source
                            elif n == target_table:
                                color = "#e74c3c"  # Red for target
                            net.add_node(n, label=n, color=color)
                        
                        # Add edges with their relation info
                        for u, v, d in path_G.edges(data=True):
                            label = f"{d.get('fk_column', '?')} -> {d.get('ref_column', '?')}"
                            net.add_edge(u, v, label=label)
                        
                        tmp = tempfile.NamedTemporaryFile(suffix=".html", delete=False)
                        net.save_graph(tmp.name)
                        html = open(tmp.name, 'r', encoding='utf-8').read()
                        st.components.v1.html(html, height=200)
                        
                        # Detailed path description
                        path_details = []
                        for j in range(len(path)-1):
                            src, dst = path[j], path[j+1]
                            edge_data = next((d for u, v, d in G.edges(data=True) 
                                           if u == src and v == dst), {})
                            fk_col = edge_data.get('fk_column', '?')
                            ref_col = edge_data.get('ref_column', '?')
                            path_details.append(f"{src}.{fk_col} -> {dst}.{ref_col}")
                        
                        st.code(" → ".join(path_details))
                else:
                    st.warning(f"No path found from {source_table} to {target_table}")
                    
                # Try reverse direction
                all_reverse_paths = list(nx.all_simple_paths(G, source=target_table, target=source_table, cutoff=4))
                if all_reverse_paths:
                    st.info(f"Found {len(all_reverse_paths)} path(s) in the reverse direction (from {target_table} to {source_table})")
                
            except nx.NetworkXNoPath:
                st.warning(f"No path found from {source_table} to {target_table}")