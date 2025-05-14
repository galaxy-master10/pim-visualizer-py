# app.py
import streamlit as st
from sqlalchemy import create_engine, MetaData, inspect
import networkx as nx
from pyvis.network import Network
import tempfile



st.set_page_config(layout="wide")
st.title("🔍 ERD Explorer")

#
# 1) Get connection string:
#
conn_str = st.text_input(
    "1) Enter your DB connection string (SQLAlchemy URI)", 
    value=""
)
if not conn_str:
    st.warning("▶️ Please paste your connection string above and press Enter.")
    st.stop()

#
# 2) Test raw connection, then reflect metadata & create inspector
#
try:
    engine = create_engine(conn_str)
    # the .connect() below will raise if creds or URI are bad
    engine.connect()
    st.success("✅ Connection OK!")
    
    # Reflect all tables
    metadata = MetaData()
    metadata.reflect(bind=engine)
    inspector = inspect(engine)
    
except Exception as e:
    st.error(f"❌ Connection or reflection failed:\n```\n{e}\n```")
    st.stop()

#
# 3) Build the directed graph of FKs
#
G = nx.DiGraph()
for tbl in metadata.sorted_tables:
    G.add_node(tbl.name)
    for fk in tbl.foreign_keys:
        parent = fk.column.table.name
        child  = tbl.name
        G.add_edge(parent, child, fk_column=fk.parent.name)

#
# 4) Sidebar controls
#
st.sidebar.header("🔧 Controls")
table_list = ["All"] + sorted(G.nodes())
selected = st.sidebar.selectbox("Focus on table", table_list)

#
# 5) Extract sub‐graph if needed
#
if selected != "All":
    neighbors = set(G.predecessors(selected)) | set(G.successors(selected))
    sub_nodes = {selected} | neighbors
    subG = G.subgraph(sub_nodes).copy()
else:
    subG = G

#
# 6) Render with PyVis
#
net = Network(height="600px", width="100%", directed=True)
for n in subG.nodes():
    net.add_node(n, label=n, title=n)
for u, v, d in subG.edges(data=True):
    net.add_edge(u, v, title=d.get("fk_column", ""))

tmp = tempfile.NamedTemporaryFile(suffix=".html", delete=False)
net.save_graph(tmp.name)
html = open(tmp.name, 'r', encoding='utf-8').read()
st.components.v1.html(html, height=600)

#
# 7) If a specific table is selected, show its columns/PK/FKs
#
if selected != "All":
    st.markdown(f"## 📋 Table Details: `{selected}`")
    cols = inspector.get_columns(selected)
    pk   = inspector.get_pk_constraint(selected).get("constrained_columns", [])
    fks  = inspector.get_foreign_keys(selected)

    st.subheader("Columns")
    st.table([{ 
        "name": c["name"], 
        "type": str(c["type"]), 
        "nullable": c["nullable"]
    } for c in cols])

    st.subheader("Primary Key")
    st.write(pk or "— no PK defined —")

    st.subheader("Foreign Keys")
    if fks:
        st.table([
            {
              "column": fk["constrained_columns"],
              "ref_table": fk["referred_table"],
              "ref_column": fk["referred_columns"]
            }
            for fk in fks
        ])
    else:
        st.write("— no FKs —")
