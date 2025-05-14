import streamlit as st
from sqlalchemy import create_engine, MetaData, inspect, Table, text
import networkx as nx
from pyvis.network import Network
import tempfile
import pandas as pd
from collections import defaultdict
import re

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
junction_tables = []
core_tables = []

# Gather all table and relationship information
for tbl in metadata.sorted_tables:
    table_name = tbl.name
    G.add_node(table_name)
    
    # Count columns
    table_cols_count[table_name] = len(tbl.columns)
    
    # Identify junction tables (contains 'X' and connects two entities)
    if 'X' in table_name:
        junction_tables.append(table_name)
    else:
        core_tables.append(table_name)
    
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

# Create a bidirectional graph for use in pathfinding
BG = G.to_undirected().to_directed()

# Find relationships established via junction tables
junction_relationships = defaultdict(list)
for jt in junction_tables:
    # Try to identify the entities this junction connects
    parts = re.split(r'X+', jt)
    if len(parts) == 2:
        entity1, entity2 = parts[0], parts[1]
        if entity1 in core_tables and entity2 in core_tables:
            junction_relationships[entity1].append({"junction": jt, "related_to": entity2})
            junction_relationships[entity2].append({"junction": jt, "related_to": entity1})

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
        
        # Include junction tables related to this table
        if 'X' not in selected:  # If this is not a junction table itself
            # Find junction tables that might connect this table
            for jt in junction_tables:
                if selected in jt:
                    sub_nodes.add(jt)
                    # Add tables on the other side of these junctions
                    for pred in G.predecessors(jt):
                        if pred != selected:
                            sub_nodes.add(pred)
                    for succ in G.successors(jt):
                        if succ != selected:
                            sub_nodes.add(succ)
            
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
        
        # Set node colors based on table type
        color = "#3498db"  # Default blue for regular tables
        if 'X' in n:
            color = "#f1c40f"  # Yellow for junction tables
        if selected != "All" and n == selected:
            color = "#e74c3c"  # Highlight selected in red
        
        net.add_node(n, label=n, title=f"Table: {n}\nColumns: {table_cols_count[n]}\nConnections: {table_fk_counts[n]}", 
                     size=size, color=color)
    
    # Add edges with optional labels
    for u, v, d in subG.edges(data=True):
        label = ""
        if show_labels:
            label = f"{d.get('fk_column', '?')} → {d.get('ref_column', '?')}"
        net.add_edge(u, v, title=f"{d.get('fk_column', '?')} → {d.get('ref_column', '?')}", label=label)

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
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Columns", table_cols_count[selected])
        col2.metric("Incoming Relations", len(list(G.predecessors(selected))))
        col3.metric("Outgoing Relations", len(list(G.successors(selected))))
        
        # If this is a junction table, show what it connects
        is_junction = 'X' in selected
        if is_junction:
            parts = re.split(r'X+', selected)
            if len(parts) >= 2:
                col4.metric("Junction Table", "Yes")
                st.info(f"This is a junction table that creates a many-to-many relationship between: {', '.join(filter(None, parts))}")
        
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
            st.write("— no foreign keys defined in this table —")
            
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
            st.write("— no tables directly reference this table —")

        # Many-to-Many Relationships section
        st.subheader("Many-to-Many Relationships")
        if 'X' not in selected:  # If this is not a junction table itself
            # Find junction tables that might connect this table
            m2m_data = []
            for jt in junction_tables:
                parts = re.split(r'X+', jt)
                if selected in parts:
                    other_entities = [part for part in parts if part and part != selected]
                    if other_entities:
                        fks_to_selected = False
                        fks_to_other = False
                        
                        # Check if this junction has FKs to both sides
                        j_fks = inspector.get_foreign_keys(jt)
                        for fk in j_fks:
                            if fk['referred_table'] == selected:
                                fks_to_selected = True
                            for other in other_entities:
                                if fk['referred_table'] == other:
                                    fks_to_other = True
                        
                        if fks_to_selected or fks_to_other:
                            m2m_info = {
                                "junction_table": jt,
                                "related_to": ", ".join(other_entities),
                                "relationship": "Complete" if (fks_to_selected and fks_to_other) else "Partial"
                            }
                            m2m_data.append(m2m_info)
            
            if m2m_data:
                st.table(pd.DataFrame(m2m_data))
                st.info("These junction tables implement many-to-many relationships between this table and other entities.")
            else:
                st.write("— no many-to-many relationships found —")
        
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
    
    # Add explanation about the database architecture pattern
    st.info("""
    ## Database Design Pattern
    
    This database follows a **many-to-many relationship pattern** using junction tables.
    
    The core tables (like Products, Attachments, etc.) don't have direct foreign keys.
    Instead, relationships between entities are established through junction tables (named with 'X' 
    between the two entity names).
    
    For example:
    - Products ⟷ ProductsXAttachments ⟷ Attachments
    - Products ⟷ ProductsXBrands ⟷ Brands
    
    This pattern allows for many-to-many relationships between entities, where a product can have
    multiple attachments, and an attachment can be associated with multiple products.
    """)
    
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
    col3.metric("Junction Tables", len(junction_tables))
    col4.metric("Isolated Tables", len(isolated_tables))
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Core Tables", len(core_tables))
    with col2:
        st.metric("Connectivity Ratio", round(total_relationships/total_tables, 2) if total_tables > 0 else 0)
    
    # Schema patterns section
    st.subheader("Schema Patterns")
    
    # Find join/bridge tables (tables with 2+ FKs and few other columns)
    join_tables = []
    for tbl in metadata.sorted_tables:
        fk_count = len([fk for fk in tbl.foreign_keys])
        non_fk_columns = len(tbl.columns) - fk_count
        if fk_count >= 2 and non_fk_columns <= 2:
            join_tables.append({
                "table": tbl.name, 
                "fk_count": fk_count, 
                "other_columns": non_fk_columns
            })
    
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
    
    # Analyze entity relationships
    st.subheader("Entity Relationship Analysis")
    
    # Count how many tables each core table is related to through junction tables
    entity_connections = {}
    for entity in core_tables:
        connected_entities = set()
        for jt in junction_tables:
            parts = re.split(r'X+', jt)
            if entity in parts:
                for part in parts:
                    if part and part != entity and part in core_tables:
                        connected_entities.add(part)
        entity_connections[entity] = len(connected_entities)
    
    # Display most connected entities
    most_connected_entities = sorted(entity_connections.items(), key=lambda x: x[1], reverse=True)[:10]
    if most_connected_entities:
        st.write("Entities with Most Relationships (through junction tables):")
        st.table(pd.DataFrame(most_connected_entities, columns=["Entity", "Connected To"]))

with tab3:
    st.header("Relationship Path Finder")
    
    col1, col2 = st.columns(2)
    with col1:
        source_table = st.selectbox("Source Table", sorted(G.nodes()), key="source")
    with col2:
        target_table = st.selectbox("Target Table", sorted(G.nodes()), key="target")
    
    # Add a depth control
    max_depth = st.slider("Maximum Path Length", min_value=1, max_value=6, value=3)
    
    # Analysis options
    include_junction = st.checkbox("Include Junction Tables", value=True)
    
    if st.button("Find Relationship Paths"):
        if source_table == target_table:
            st.warning("Source and target tables are the same")
        else:
            try:
                # Determine which graph to use based on user preferences
                graph_to_use = BG if include_junction else G
                
                # Find all paths between source and target
                all_paths = list(nx.all_simple_paths(graph_to_use, source=source_table, 
                                                    target=target_table, cutoff=max_depth))
                
                if all_paths:
                    st.success(f"Found {len(all_paths)} path(s) from {source_table} to {target_table}")
                    
                    # Sort paths by length (shorter paths first)
                    all_paths.sort(key=len)
                    
                    for i, path in enumerate(all_paths[:10]):  # Show up to 10 paths
                        st.subheader(f"Path {i+1} ({len(path)-1} hops)")
                        
                        # Create a visualization of this path
                        path_G = nx.DiGraph()
                        path_details = []
                        
                        for j in range(len(path)-1):
                            src, dst = path[j], path[j+1]
                            
                            # Check both directions for the edge
                            edge_data = {}
                            for u, v, d in graph_to_use.edges(data=True):
                                if u == src and v == dst:
                                    edge_data = d
                                    break
                            
                            path_G.add_edge(src, dst, **edge_data)
                            
                            # Check if this is a junction table (contains 'X' in name)
                            is_junction = 'X' in src or 'X' in dst
                            
                            # Format path description
                            fk_col = edge_data.get('fk_column', '?')
                            ref_col = edge_data.get('ref_column', '?')
                            
                            if is_junction:
                                if src in core_tables and dst in junction_tables:
                                    path_details.append(f"{src} → {dst}")
                                elif src in junction_tables and dst in core_tables:
                                    path_details.append(f"{src} → {dst}")
                                else:
                                    path_details.append(f"{src}.{fk_col} → {dst}.{ref_col}")
                            else:
                                path_details.append(f"{src}.{fk_col} → {dst}.{ref_col}")
                        
                        # Render path diagram
                        net = Network(height="200px", width="100%", directed=True)
                        for n in path_G.nodes():
                            color = "#3498db"  # Default blue
                            if n == source_table:
                                color = "#2ecc71"  # Green for source
                            elif n == target_table:
                                color = "#e74c3c"  # Red for target
                            elif "X" in n:
                                color = "#f1c40f"  # Yellow for junction tables
                            net.add_node(n, label=n, color=color)
                        
                        # Add edges
                        for u, v, d in path_G.edges(data=True):
                            net.add_edge(u, v)
                        
                        tmp = tempfile.NamedTemporaryFile(suffix=".html", delete=False)
                        net.save_graph(tmp.name)
                        html = open(tmp.name, 'r', encoding='utf-8').read()
                        st.components.v1.html(html, height=200)
                        
                        # Detailed path description
                        st.code(" → ".join(path_details))
                        
                        # Add explanation for junction tables
                        junction_tables_in_path = [n for n in path if 'X' in n]
                        if junction_tables_in_path:
                            st.info(f"This path goes through {len(junction_tables_in_path)} junction/bridge tables: {', '.join(junction_tables_in_path)}")
                            
                            # Try to interpret the relationship semantically
                            if len(path) == 3 and 'X' in path[1]:
                                # This is a direct many-to-many relationship
                                junction = path[1]
                                st.success(f"This represents a many-to-many relationship between {source_table} and {target_table} via the {junction} junction table.")
                                
                                # Attempt to show relationship data if available
                                try:
                                    with engine.connect() as conn:
                                        q = text(f"""
                                        SELECT COUNT(*) as count 
                                        FROM [{junction}]
                                        """)
                                        result = conn.execute(q).fetchone()
                                        if result and result[0] > 0:
                                            st.write(f"There are {result[0]} relationships in this junction table.")
                                except:
                                    pass
                else:
                    st.warning(f"No path found from {source_table} to {target_table}")
                    
                    # Try reverse direction if using directed graph
                    if not include_junction:
                        all_reverse_paths = list(nx.all_simple_paths(G, source=target_table, target=source_table, cutoff=max_depth))
                        if all_reverse_paths:
                            st.info(f"Found {len(all_reverse_paths)} path(s) in the reverse direction (from {target_table} to {source_table})")
                            st.write("Try checking the 'Include Junction Tables' option to find indirect relationships.")
            
            except nx.NetworkXNoPath:
                st.warning(f"No path found from {source_table} to {target_table}")
                
                # Suggest alternatives
                if not include_junction:
                    st.write("Try checking the 'Include Junction Tables' option to find indirect relationships.")
                else:
                    # Find shortest path through any table
                    try:
                        # Construct undirected graph for finding any connection
                        UG = G.to_undirected()
                        if nx.has_path(UG, source_table, target_table):
                            path = nx.shortest_path(UG, source_table, target_table)
                            st.info(f"These tables are connected, but not by direct foreign keys. They're connected through {len(path)-2} intermediate tables.")
                    except:
                        st.error("No connection found between these tables in the database.")