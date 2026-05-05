import streamlit as st
import requests
import pandas as pd

BACKEND_URL = "http://localhost:5000"

st.set_page_config(page_title="Compiler Phases", page_icon="⚙️", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Space+Grotesk:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Space Grotesk', sans-serif; }
    .stTextArea textarea { font-family: 'JetBrains Mono', monospace !important; font-size: 13px !important; }
    .token-badge { display:inline-block; padding:3px 10px; border-radius:4px; font-family:'JetBrains Mono',monospace; font-size:12px; margin:2px; }
    .stButton > button { background:linear-gradient(135deg,#1e3a5f,#2563eb); color:white; border:none; border-radius:6px; font-weight:600; padding:0.5rem 2rem; font-size:15px; }
    .error-box { background:#3d1f1f; border:1px solid #f85149; border-radius:6px; padding:10px 14px; color:#f85149; font-family:'JetBrains Mono',monospace; font-size:13px; margin:4px 0; }
    .warning-box { background:#3d3010; border:1px solid #f2cc60; border-radius:6px; padding:10px 14px; color:#f2cc60; font-family:'JetBrains Mono',monospace; font-size:13px; margin:4px 0; }
    .success-box { background:#1a3d1f; border:1px solid #3fb950; border-radius:6px; padding:10px 14px; color:#3fb950; font-family:'JetBrains Mono',monospace; font-size:13px; margin:4px 0; }
    .phase-header { background:linear-gradient(135deg,#1e3a5f,#2563eb); color:white; padding:12px 20px; border-radius:8px; margin-bottom:16px; }
</style>
""", unsafe_allow_html=True)

TOKEN_COLORS = {
    "KEYWORD": ("#ff7b72", "#3d1f1f"),
    "IDENTIFIER": ("#79c0ff", "#1a2c3d"),
    "INTEGER": ("#f2cc60", "#3d3010"),
    "FLOAT": ("#ffa657", "#3d2510"),
    "STRING": ("#a5d6ff", "#1a2535"),
    "OPERATOR": ("#d2a8ff", "#2d1f3d"),
    "DELIMITER": ("#8b949e", "#1f2328"),
    "UNKNOWN": ("#f85149", "#3d1010"),
}

SAMPLES = {
    "Grade Calculator": """def calculate_grade(marks):
    if marks >= 90:
        grade = "A+"
    elif marks >= 75:
        grade = "A"
    elif marks >= 60:
        grade = "B"
    else:
        grade = "F"
    return grade

score = 85
result = calculate_grade(score)
print(result)""",

    "Fibonacci": """def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)

result = fibonacci(10)
print(result)""",

    "For Loop": """total = 0
for i in range(10):
    total = total + i
print(total)""",
}

# ── Sidebar ──────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Compiler Phases")
    st.markdown("**Select a phase to analyse your code**")
    st.markdown("---")
    phase = st.radio("", [
        "1️⃣  Tokenization (Lexical Analysis)",
        "2️⃣  Syntax Analysis (Parsing)",
        "3️⃣  Semantic Analysis",
        "4️⃣  Intermediate Code Generation",
    ])
    st.markdown("---")
    st.markdown("### 📌 Phase Guide")
    st.markdown("""
- **Phase 1** — Breaks code into tokens
- **Phase 2** — Checks grammar, builds AST
- **Phase 3** — Checks meaning & scope
- **Phase 4** — Generates Three Address Code
    """)

# ── Input Area ───────────────────────────────────────
st.title("⚙️ Compiler Phase Analyser")
st.caption("Perform all 4 phases of a compiler on your Python code")
st.markdown("---")

col_input, col_output = st.columns([1, 1], gap="large")

with col_input:
    st.markdown("### 📝 Source Code")
    sample_choice = st.selectbox("Load a sample", ["— custom —"] + list(SAMPLES.keys()))
    default_code = SAMPLES.get(sample_choice, "") if sample_choice != "— custom —" else ""
    source_code = st.text_area("Code", value=default_code, height=320, label_visibility="collapsed")
    run_btn = st.button("▶ Run Phase", use_container_width=True)

# ── Output Area ──────────────────────────────────────
with col_output:
    # ── PHASE 1: TOKENIZATION ──────────────────────
    if "1️⃣" in phase:
        st.markdown('<div class="phase-header">🔤 Phase 1 — Tokenization (Lexical Analysis)</div>',
                    unsafe_allow_html=True)

        if run_btn and source_code.strip():
            with st.spinner("Tokenizing..."):
                try:
                    resp = requests.post(f"{BACKEND_URL}/tokenize", json={"source_code": source_code}, timeout=5)
                    st.session_state["tok_result"] = resp.json()
                except Exception as e:
                    st.error(f"Cannot connect to backend: {e}")

        if "tok_result" in st.session_state:
            res = st.session_state["tok_result"]
            errors = res.get("errors", [])

            if errors:
                st.markdown("#### ❌ Lexical Errors")
                for err in errors:
                    st.markdown(f'<div class="error-box">⚠ {err}</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="success-box">✓ No lexical errors found</div>', unsafe_allow_html=True)

            summary = res.get("summary", {})
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("KEYWORD", summary.get("KEYWORD", 0))
            c2.metric("IDENTIFIER", summary.get("IDENTIFIER", 0))
            c3.metric("OPERATOR", summary.get("OPERATOR", 0))
            c4.metric("Total", res.get("total", 0))

            tokens = res.get("tokens", [])
            st.markdown("**Token Stream:**")
            html = " ".join([
                f'<span class="token-badge" style="background:{TOKEN_COLORS.get(t["type"], ("#8b949e", "#1f2328"))[1]};color:{TOKEN_COLORS.get(t["type"], ("#8b949e", "#1f2328"))[0]};border:1px solid {TOKEN_COLORS.get(t["type"], ("#8b949e", "#1f2328"))[0]}44">{t["value"]}</span>'
                for t in tokens
            ])
            st.markdown(html, unsafe_allow_html=True)

            st.markdown("**Token Table:**")
            df = pd.DataFrame([{"Line": t["line"], "Token Type": t["type"], "Lexeme": t["value"]} for t in tokens])
            df.index += 1
            st.dataframe(df, use_container_width=True, height=300)

    # ── PHASE 2: SYNTAX ANALYSIS ───────────────────
    elif "2️⃣" in phase:
        st.markdown('<div class="phase-header">🌳 Phase 2 — Syntax Analysis (Parsing)</div>', unsafe_allow_html=True)

        if run_btn and source_code.strip():
            with st.spinner("Parsing..."):
                try:
                    resp = requests.post(f"{BACKEND_URL}/syntax", json={"source_code": source_code}, timeout=5)
                    st.session_state["syn_result"] = resp.json()
                except Exception as e:
                    st.error(f"Cannot connect to backend: {e}")

        if "syn_result" in st.session_state:
            res = st.session_state["syn_result"]
            error = res.get("error")

            if error:
                st.markdown("#### ❌ Syntax Error")
                st.markdown(f'<div class="error-box">⚠ {error}</div>', unsafe_allow_html=True)
                st.info("Fix the syntax error above and re-run.")
            else:
                st.markdown(
                    f'<div class="success-box">✓ Syntax valid — {res.get("node_count", 0)} AST nodes generated</div>',
                    unsafe_allow_html=True)

                # ── SYNTAX TREE VISUALIZATION ──
                st.markdown("### 🌳 Syntax Tree")
                ast_data = res.get("ast", [])

                tree_html = '<div style="background:#0a0e27; border:1px solid #1e3a8a; border-radius:8px; padding:16px; font-family:\'Courier New\',monospace; color:#e0e7ff; margin:12px 0; overflow-x:auto;">'

                for row in ast_data:
                    depth = row.get("Depth", 0)
                    node_type = row.get("Node Type", "?")
                    desc = row.get("Description", "")

                    # Color code by node type
                    if node_type == "Program":
                        color = "#60a5fa"  # blue
                    elif node_type == "FunctionDef":
                        color = "#34d399"  # green
                    elif "Loop" in node_type:
                        color = "#fbbf24"  # amber
                    elif "Statement" in node_type or "If" in node_type:
                        color = "#f87171"  # red
                    elif node_type == "FunctionCall":
                        color = "#c084fc"  # purple
                    elif node_type == "VarDeclaration":
                        color = "#06b6d4"  # cyan
                    elif node_type == "Preprocessor":
                        color = "#a78bfa"  # violet
                    else:
                        color = "#cbd5e1"  # slate

                    # Build tree with indentation
                    indent = "│   " * depth
                    prefix = "├── " if depth > 0 else ""

                    label = f"<span style='color:{color}; font-weight:bold'>{node_type}</span>"
                    if desc:
                        label += f" <span style='color:#94a3b8; font-size:0.9em'>{desc}</span>"

                    tree_html += f'<div style="margin:6px 0; margin-left:{depth * 20}px;">{prefix}{label}</div>'

                tree_html += '</div>'
                st.markdown(tree_html, unsafe_allow_html=True)

                # ── LEGEND ──
                st.markdown("**Node Types Legend:**")
                leg_cols = st.columns(5)
                legends = [
                    ("Program", "#60a5fa"),
                    ("Function", "#34d399"),
                    ("Loop", "#fbbf24"),
                    ("Statement", "#f87171"),
                    ("Call", "#c084fc"),
                ]
                for col, (name, color) in zip(leg_cols, legends):
                    col.markdown(
                        f'<div style="background:{color}22; border-left:3px solid {color}; padding:6px 10px; border-radius:4px; font-size:0.9em;"><span style="color:{color}">■</span> {name}</div>',
                        unsafe_allow_html=True)

                # ── TABLE VIEW ──
                st.markdown("### 📊 AST Details Table")
                df = pd.DataFrame([{"#": i + 1, "Depth": r.get("Depth", ""), "Node Type": r.get("Node Type", ""),
                                    "Description": r.get("Description", "")} for i, r in enumerate(ast_data)])
                st.dataframe(df, use_container_width=True, height=300)

    # ── PHASE 3: SEMANTIC ANALYSIS ─────────────────
    elif "3️⃣" in phase:
        st.markdown('<div class="phase-header">🔍 Phase 3 — Semantic Analysis</div>', unsafe_allow_html=True)

        if run_btn and source_code.strip():
            with st.spinner("Analysing semantics..."):
                try:
                    resp = requests.post(f"{BACKEND_URL}/semantic", json={"source_code": source_code}, timeout=5)
                    st.session_state["sem_result"] = resp.json()
                except Exception as e:
                    st.error(f"Cannot connect to backend: {e}")

        if "sem_result" in st.session_state:
            res = st.session_state["sem_result"]
            errors = res.get("errors", [])
            warnings = res.get("warnings", [])
            symbols = res.get("symbols", [])

            if errors:
                st.markdown("#### ❌ Semantic Errors")
                for err in errors:
                    st.markdown(f'<div class="error-box">⚠ {err}</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="success-box">✓ No semantic errors found</div>', unsafe_allow_html=True)

            if warnings:
                st.markdown("#### ⚠️ Warnings")
                for w in warnings:
                    st.markdown(f'<div class="warning-box">⚡ {w}</div>', unsafe_allow_html=True)

            if symbols:
                st.markdown("**Symbol Table:**")
                df = pd.DataFrame(symbols)
                df.index += 1
                st.dataframe(df, use_container_width=True, height=300)

    # ── PHASE 4: CODE GENERATION ───────────────────
    elif "4️⃣" in phase:
        st.markdown('<div class="phase-header">💻 Phase 4 — Intermediate Code Generation (TAC)</div>',
                    unsafe_allow_html=True)

        if run_btn and source_code.strip():
            with st.spinner("Generating code..."):
                try:
                    resp = requests.post(f"{BACKEND_URL}/codegen", json={"source_code": source_code}, timeout=5)
                    st.session_state["cg_result"] = resp.json()
                except Exception as e:
                    st.error(f"Cannot connect to backend: {e}")

        if "cg_result" in st.session_state:
            res = st.session_state["cg_result"]
            error = res.get("error")

            if error:
                st.markdown("#### ❌ Error")
                st.markdown(f'<div class="error-box">⚠ {error}</div>', unsafe_allow_html=True)
            else:
                tac = res.get("tac", [])
                st.markdown(
                    f'<div class="success-box">✓ {res.get("instruction_count", 0)} TAC instructions generated</div>',
                    unsafe_allow_html=True)
                st.markdown("**Three Address Code (TAC):**")
                tac_text = "\n".join([row["Instruction"] for row in tac])
                st.code(tac_text, language="text")
                st.markdown("**Instruction Table:**")
                df = pd.DataFrame(tac)
                df.index += 1
                st.dataframe(df, use_container_width=True, height=350)

if run_btn and not source_code.strip():
    with col_output:
        st.warning("Please enter some source code first.")