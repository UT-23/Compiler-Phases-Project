from flask import Flask, request, jsonify
from flask_cors import CORS
import re, os, sqlite3, datetime

app = Flask(__name__)
CORS(app)
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "compiler.db")

C_KEYWORDS = {
    "int","float","double","char","void","if","else","while","for","do",
    "return","printf","scanf","include","define","main","break","continue",
    "switch","case","default","struct","typedef","sizeof","long","short",
    "unsigned","signed","const","static","extern","auto","register","enum",
    "union","goto","volatile","NULL","EOF"
}

C_TOKEN_PATTERNS = [
    ("PREPROCESSOR", r'#\s*(include|define|ifdef|ifndef|endif|pragma)[^\n]*'),
    ("COMMENT",      r'//[^\n]*|/\*[\s\S]*?\*/'),
    ("STRING",       r'"[^"]*"'),
    ("CHAR_LIT",     r"'[^']*'"),
    ("FLOAT",        r'\b\d+\.\d+([eE][+-]?\d+)?\b'),
    ("INTEGER",      r'\b\d+\b'),
    ("OPERATOR",     r'==|!=|<=|>=|&&|\|\||<<|>>|\+\+|--|->|\+=|-=|\*=|/=|%=|[+\-*/%=<>!&|^~]'),
    ("DELIMITER",    r'[(){}\[\],;:.]'),
    ("IDENTIFIER",   r'\b[a-zA-Z_][a-zA-Z0-9_]*\b'),
    ("WHITESPACE",   r'\s+'),
    ("UNKNOWN",      r'.'),
]

def tokenize_c(source_code):
    tokens, pos, line, col = [], 0, 1, 1
    while pos < len(source_code):
        matched = False
        for token_type, pattern in C_TOKEN_PATTERNS:
            m = re.compile(pattern).match(source_code, pos)
            if m:
                value = m.group(0)
                if token_type in ("WHITESPACE", "COMMENT"):
                    nl = value.count('\n')
                    line += nl
                    col = len(value) - value.rfind('\n') if nl else col + len(value)
                    pos = m.end(); matched = True; break
                actual_type = "KEYWORD" if token_type == "IDENTIFIER" and value in C_KEYWORDS else token_type
                tokens.append({"type": actual_type, "value": value, "line": line, "col": col})
                col += len(value); pos = m.end(); matched = True; break
        if not matched: pos += 1
    return tokens

@app.route("/tokenize", methods=["POST"])
def tokenize_route():
    data = request.get_json()
    source_code = data.get("source_code", "")
    if not source_code.strip():
        return jsonify({"error": "No source code provided"}), 400
    tokens = tokenize_c(source_code)
    errors = [f"Line {t['line']}: Unknown character '{t['value']}'" for t in tokens if t["type"] == "UNKNOWN"]
    summary = {}
    for t in tokens:
        summary[t["type"]] = summary.get(t["type"], 0) + 1
    return jsonify({"tokens": tokens, "summary": summary, "total": len(tokens), "errors": errors})

def syntax_analysis_c(source_code):
    errors = []
    ast_nodes = []
    # Balanced brackets check
    stack = []
    pairs = {')':'(', '}':'{', ']':'['}
    lines = source_code.split('\n')
    for lno, line in enumerate(lines, 1):
        clean = re.sub(r'"[^"]*"','""', line)
        clean = re.sub(r"'[^']*'","''", clean)
        clean = re.sub(r'//.*','', clean)
        for ch in clean:
            if ch in '({[': stack.append((ch, lno))
            elif ch in ')}]':
                if not stack: errors.append(f"Line {lno}: Unexpected '{ch}' — no matching opening bracket")
                elif stack[-1][0] != pairs[ch]: errors.append(f"Line {lno}: Mismatched bracket '{ch}'"); stack.pop()
                else: stack.pop()
    for ch, ln in stack:
        errors.append(f"Line {ln}: Unclosed '{ch}' — missing closing bracket")

    # Missing semicolons
    for lno, line in enumerate(lines, 1):
        s = line.strip()
        if not s or s.startswith('//') or s.startswith('#') or s.startswith('/*') or s.startswith('*'): continue
        no_semi = any([s.endswith('{'), s.endswith('}'), s.startswith('if'), s.startswith('else'),
                       s.startswith('for'), s.startswith('while'), s.startswith('do'), s == ''])
        has_stmt = re.search(r'(=|printf|scanf|return|\+\+|--)', s)
        if has_stmt and not no_semi and not s.endswith(';') and not s.endswith('{') and not s.endswith('}'):
            errors.append(f"Line {lno}: Possible missing semicolon — '{s[:50]}'")

    if 'main' not in source_code:
        errors.append("No 'main' function found")

    # Build AST nodes
    nid = 1
    ast_nodes.append({"#": nid, "Node Type": "Program", "Description": "Root — Translation Unit", "Depth": 0}); nid+=1
    for m in re.finditer(r'#include\s*[<"][^>"]+[>"]', source_code):
        ast_nodes.append({"#": nid, "Node Type": "Preprocessor", "Description": m.group(0).strip(), "Depth": 1}); nid+=1
    for m in re.finditer(r'\b(int|void|float|char|double)\s+(\w+)\s*\(([^)]*)\)', source_code):
        ln = source_code[:m.start()].count('\n') + 1
        ast_nodes.append({"#": nid, "Node Type": "FunctionDef", "Description": f"{m.group(1)} {m.group(2)}({m.group(3)}) at line {ln}", "Depth": 1}); nid+=1
        decl_pat = re.compile(r'\b(int|float|double|char|long|short)\s+([\w\s,=\[\]]+);')
        body = source_code[m.end():m.end()+800]
        for dm in decl_pat.finditer(body):
            ast_nodes.append({"#": nid, "Node Type": "VarDeclaration", "Description": f"{dm.group(1)} {dm.group(2).strip()}", "Depth": 2}); nid+=1
    for m in re.finditer(r'\bfor\s*\(', source_code):
        ln = source_code[:m.start()].count('\n') + 1
        ast_nodes.append({"#": nid, "Node Type": "ForLoop", "Description": f"for loop at line {ln}", "Depth": 2}); nid+=1
    for m in re.finditer(r'\bwhile\s*\(', source_code):
        ln = source_code[:m.start()].count('\n') + 1
        ast_nodes.append({"#": nid, "Node Type": "WhileLoop", "Description": f"while loop at line {ln}", "Depth": 2}); nid+=1
    for m in re.finditer(r'\bif\s*\(', source_code):
        ln = source_code[:m.start()].count('\n') + 1
        ast_nodes.append({"#": nid, "Node Type": "IfStatement", "Description": f"if statement at line {ln}", "Depth": 2}); nid+=1
    for m in re.finditer(r'\b(printf|scanf)\s*\(', source_code):
        ln = source_code[:m.start()].count('\n') + 1
        ast_nodes.append({"#": nid, "Node Type": "FunctionCall", "Description": f"{m.group(1)}() at line {ln}", "Depth": 3}); nid+=1
    for m in re.finditer(r'\breturn\b', source_code):
        ln = source_code[:m.start()].count('\n') + 1
        ast_nodes.append({"#": nid, "Node Type": "ReturnStmt", "Description": f"return at line {ln}", "Depth": 3}); nid+=1

    return errors, ast_nodes

@app.route("/syntax", methods=["POST"])
def syntax_route():
    data = request.get_json()
    source_code = data.get("source_code", "")
    if not source_code.strip():
        return jsonify({"error": "No source code provided"}), 400
    errors, ast_nodes = syntax_analysis_c(source_code)
    return jsonify({"ast": ast_nodes, "all_errors": errors, "error": errors[0] if errors else None, "success": len(errors)==0, "node_count": len(ast_nodes)})

def semantic_analysis_c(source_code):
    errors, warnings, symbols = [], [], []
    decl_pat = re.compile(r'\b(int|float|double|char|long|short|unsigned)\s+([\w\s,=\[\]*]+);')
    declared_vars = {}
    for m in decl_pat.finditer(source_code):
        dtype = m.group(1)
        ln = source_code[:m.start()].count('\n') + 1
        for var in re.split(r'\s*,\s*', m.group(2)):
            vname = re.split(r'[\s=\[\*]', var.strip())[0].strip()
            if vname and re.match(r'^[a-zA-Z_]\w*$', vname):
                declared_vars[vname] = {"type": dtype, "line": ln}
                count = len(re.findall(r'\b' + re.escape(vname) + r'\b', source_code))
                symbols.append({"Name": vname, "Kind": "variable", "Type": dtype, "Line": ln, "Used": "Yes" if count > 1 else "No"})
    func_pat = re.compile(r'\b(int|void|float|char|double)\s+(\w+)\s*\(([^)]*)\)')
    declared_funcs = {}
    for m in func_pat.finditer(source_code):
        fname = m.group(2)
        ln = source_code[:m.start()].count('\n') + 1
        declared_funcs[fname] = {"return_type": m.group(1), "line": ln}
        symbols.append({"Name": fname, "Kind": "function", "Type": m.group(1), "Line": ln, "Used": "Yes"})
        params = m.group(3).strip()
        if params and params not in ("void", ""):
            for param in params.split(','):
                parts = param.strip().split()
                if len(parts) >= 2:
                    pname = parts[-1].replace('*','').replace('[','').replace(']','')
                    if re.match(r'^[a-zA-Z_]\w*$', pname):
                        symbols.append({"Name": pname, "Kind": "parameter", "Type": parts[0], "Line": ln, "Used": "Yes"})
    c_keywords = {"int","float","double","char","void","if","else","while","for","do","return","printf","scanf",
                  "include","define","main","break","continue","switch","case","default","struct","typedef",
                  "sizeof","long","short","unsigned","signed","const","static","NULL","EOF","stderr","stdout","STR","stdio","h"}
    # Strip string contents before extracting identifiers to avoid false positives
    # Remove all string/char literals and comments before identifier scanning
    code_no_strings = source_code
    code_no_strings = re.sub(r'"[^"\n]*"', '', code_no_strings)
    code_no_strings = re.sub(r"'[^'\n]*'", '', code_no_strings)
    code_no_strings = re.sub(r'//[^\n]*', '', code_no_strings)
    code_no_strings = re.sub(r'/\*[\s\S]*?\*/', '', code_no_strings)
    code_no_strings = re.sub(r'#[^\n]*', '', code_no_strings)
    all_identifiers = set(re.findall(r'\b([a-zA-Z_]\w*)\b', code_no_strings))
    for ident in all_identifiers:
        # Skip single characters, numbers, and common false positives
        if len(ident) <= 1: continue
        if ident not in c_keywords and ident not in declared_vars and ident not in declared_funcs:
            for m in re.finditer(r'\b' + re.escape(ident) + r'\b', code_no_strings):
                context = code_no_strings[max(0,m.start()-30):m.end()+30]
                if not re.search(r'(int|float|char|double|void|long|short)\s+' + re.escape(ident), context):
                    if not re.search(r'#include|#define', context):
                        ln = source_code[:m.start()].count('\n') + 1
                        errors.append(f"Line {ln}: '{ident}' used but not declared")
                break
    for vname, info in declared_vars.items():
        count = len(re.findall(r'\b' + re.escape(vname) + r'\b', source_code))
        if count <= 1:
            warnings.append(f"Line {info['line']}: Variable '{vname}' declared but never used")
    return errors, warnings, symbols

@app.route("/semantic", methods=["POST"])
def semantic_route():
    data = request.get_json()
    source_code = data.get("source_code", "")
    if not source_code.strip():
        return jsonify({"error": "No source code provided"}), 400
    errors, warnings, symbols = semantic_analysis_c(source_code)
    return jsonify({"errors": errors, "warnings": warnings, "symbols": symbols, "success": len(errors)==0})

def split_on_op(expr, op):
    depth = 0
    i = 0
    while i < len(expr):
        c = expr[i]
        if c in '([': depth += 1
        elif c in ')]': depth -= 1
        elif depth == 0 and expr[i:i+len(op)] == op:
            left = expr[:i].strip()
            right = expr[i+len(op):].strip()
            if left and right:
                return left, right
        i += 1
    return None

def process_expr(expr, new_temp, emit):
    expr = expr.strip()
    for op in ['==','!=','<=','>=','&&','||','<','>','+','-','*','/','%']:
        parts = split_on_op(expr, op)
        if parts:
            left = process_expr(parts[0], new_temp, emit)
            right = process_expr(parts[1], new_temp, emit)
            t = new_temp()
            emit(f"  {t} = {left} {op} {right}")
            return t
    return expr

def generate_tac_c(source_code):
    tac = []
    temp_count = [0]
    label_count = [0]
    def new_temp():
        temp_count[0] += 1; return f"t{temp_count[0]}"
    def new_label():
        label_count[0] += 1; return f"L{label_count[0]}"
    def emit(i): tac.append(i)

    for line in source_code.split('\n'):
        s = line.strip()
        if not s or s.startswith('//') or s.startswith('/*') or s.startswith('*'): continue
        if s.startswith('#'):
            emit(f"; {s}"); continue
        m = re.match(r'\b(int|void|float|char|double)\s+(\w+)\s*\(([^)]*)\)\s*\{?', s)
        if m and m.group(2) not in ('printf','scanf'):
            emit(f"FUNC_BEGIN {m.group(2)}")
            for p in m.group(3).split(','):
                pn = p.strip().split()[-1].replace('*','') if p.strip() and p.strip()!='void' else ''
                if pn and re.match(r'^[a-zA-Z_]\w*$', pn): emit(f"  PARAM {pn}")
            continue
        if s == '}': emit("FUNC_END"); continue
        m = re.match(r'\b(int|float|double|char)\s+(\w+)\s*=\s*(.+);', s)
        if m:
            v = process_expr(m.group(3).strip(), new_temp, emit)
            emit(f"  {m.group(2)} = {v}"); continue
        m = re.match(r'\b(int|float|double|char)\s+([\w\s,]+);', s)
        if m:
            for var in m.group(2).split(','):
                v = var.strip()
                if v: emit(f"  DECLARE {m.group(1)} {v}")
            continue
        m = re.match(r'^(\w+)\s*=\s*(.+);$', s)
        if m and not re.search(r'\b(int|float|char|double)\b', s):
            v = process_expr(m.group(2).strip(), new_temp, emit)
            emit(f"  {m.group(1)} = {v}"); continue
        m = re.match(r'^(\w+)\s*(\+=|-=|\*=|/=|%=)\s*(.+);$', s)
        if m:
            ops = {"+=":"+","-=":"-","*=":"*","/=":"/","%=":"%"}
            v = process_expr(m.group(3).strip(), new_temp, emit)
            t = new_temp(); emit(f"  {t} = {m.group(1)} {ops.get(m.group(2))} {v}"); emit(f"  {m.group(1)} = {t}"); continue
        m = re.match(r'^(\w+)(\+\+|--);\s*$', s)
        if m:
            op = "+" if m.group(2)=="++" else "-"; t = new_temp()
            emit(f"  {t} = {m.group(1)} {op} 1"); emit(f"  {m.group(1)} = {t}"); continue
        m = re.match(r'for\s*\(([^;]*);([^;]*);([^)]*)\)\s*\{?', s)
        if m:
            sl = new_label(); el = new_label()
            im = re.match(r'(?:int\s+)?(\w+)\s*=\s*(.+)', m.group(1).strip())
            if im: emit(f"  {im.group(1)} = {im.group(2)}")
            emit(f"{sl}:")
            if m.group(2).strip():
                t = process_expr(m.group(2).strip(), new_temp, emit); emit(f"  IF_FALSE {t} GOTO {el}")
            emit(f"  ; for-body"); emit(f"  GOTO {sl}"); emit(f"{el}:"); continue
        m = re.match(r'while\s*\((.+)\)\s*\{?', s)
        if m:
            sl = new_label(); el = new_label(); emit(f"{sl}:")
            t = process_expr(m.group(1).strip(), new_temp, emit)
            emit(f"  IF_FALSE {t} GOTO {el}"); emit(f"  ; while-body"); emit(f"  GOTO {sl}"); emit(f"{el}:"); continue
        m = re.match(r'else\s+if\s*\((.+)\)\s*\{?', s)
        if m:
            lbl = new_label(); t = process_expr(m.group(1).strip(), new_temp, emit)
            emit(f"  IF_FALSE {t} GOTO {lbl}"); emit(f"  ; else-if body"); emit(f"{lbl}:"); continue
        m = re.match(r'if\s*\((.+)\)\s*\{?', s)
        if m:
            el = new_label(); endl = new_label()
            t = process_expr(m.group(1).strip(), new_temp, emit)
            emit(f"  IF_FALSE {t} GOTO {el}"); emit(f"  ; if-body"); emit(f"  GOTO {endl}"); emit(f"{el}:"); emit(f"{endl}:"); continue
        if s in ('else','else {'): emit("  ; else-body"); continue
        m = re.match(r'(printf|scanf)\s*\((.+)\);', s)
        if m: emit(f"  CALL {m.group(1)} [{m.group(2)[:35]}]"); continue
        m = re.match(r'return\s*(.*);', s)
        if m: emit(f"  RETURN {m.group(1).strip()}" if m.group(1).strip() else "  RETURN"); continue

    return [{"#": i+1, "Instruction": instr} for i, instr in enumerate(tac)]

@app.route("/codegen", methods=["POST"])
def codegen_route():
    data = request.get_json()
    source_code = data.get("source_code", "")
    if not source_code.strip():
        return jsonify({"error": "No source code provided"}), 400
    tac = generate_tac_c(source_code)
    return jsonify({"tac": tac, "error": None, "success": True, "instruction_count": len(tac)})

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS runs (id INTEGER PRIMARY KEY AUTOINCREMENT, phase TEXT, source_code TEXT, created_at TEXT)''')
    conn.commit(); conn.close()

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    init_db()
    print("Compiler backend running on http://localhost:5000")
    app.run(debug=True, port=5000)