from flask import Flask, request, jsonify
from flask_cors import CORS
import re

app = Flask(__name__)
CORS(app)


@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"}), 200


@app.route('/tokenize', methods=['POST'])
def tokenize():
    try:
        code = request.json.get('source_code', '')
        if not code: return jsonify({"error": "No code", "tokens": [], "summary": {}, "total": 0}), 400

        tokens = []
        pos = 0
        line = 1
        col = 1

        patterns = [
            ("KEYWORD", r'\b(int|float|char|void|if|else|while|for|return|printf|scanf|main|include)\b'),
            ("INTEGER", r'\b\d+\b'),
            ("FLOAT", r'\b\d+\.\d+\b'),
            ("STRING", r'"[^"]*"'),
            ("OPERATOR", r'(==|!=|<=|>=|\+\+|--|&&|\|\||->|[+\-*/%=<>!&|])'),
            ("DELIMITER", r'[(){}\[\];,:]'),
            ("IDENTIFIER", r'[a-zA-Z_]\w*'),
            ("WHITESPACE", r'\s+'),
        ]

        while pos < len(code):
            matched = False
            for typ, pat in patterns:
                m = re.compile(pat).match(code, pos)
                if m:
                    val = m.group(0)
                    if typ != "WHITESPACE":
                        tokens.append({"type": typ, "value": val, "line": line, "col": col})
                    if '\n' in val:
                        line += val.count('\n')
                        col = 1
                    else:
                        col += len(val)
                    pos = m.end()
                    matched = True
                    break
            if not matched: pos += 1

        summary = {}
        for t in tokens:
            summary[t['type']] = summary.get(t['type'], 0) + 1

        return jsonify({"tokens": tokens, "summary": summary, "total": len(tokens), "error": None}), 200
    except Exception as e:
        return jsonify({"error": str(e), "tokens": [], "summary": {}, "total": 0}), 500


@app.route('/icdg', methods=['POST'])
def icdg():
    try:
        code = request.json.get('source_code', '')
        if not code: return jsonify({"error": "No code", "tac": [], "instruction_count": 0}), 400

        tac = []
        for line in code.split('\n'):
            s = line.strip()
            if not s or s.startswith('//'): continue
            if s.startswith('#'):
                tac.append(f"; {s}")
            elif 'main' in s:
                tac.append("FUNC_BEGIN main")
            elif s == '}':
                tac.append("FUNC_END")
            elif '=' in s and 'if' not in s:
                tac.append(f"  {s.rstrip(';')}")
            elif 'for' in s:
                tac.append("; FOR")
            elif 'while' in s:
                tac.append("; WHILE")
            elif 'if' in s:
                tac.append("; IF")
            elif 'printf' in s:
                tac.append("; CALL printf")
            elif 'return' in s:
                tac.append("; RETURN")

        fmt = [{"#": i + 1, "Instruction": x} for i, x in enumerate(tac)]
        return jsonify({"tac": fmt, "instruction_count": len(tac), "error": None}), 200
    except Exception as e:
        return jsonify({"error": str(e), "tac": [], "instruction_count": 0}), 500


@app.route('/optimize', methods=['POST'])
def optimize():
    try:
        code = request.json.get('source_code', '')
        if not code: return jsonify({"error": "No code", "optimized": [], "removed": 0}), 400

        tac = []
        for line in code.split('\n'):
            s = line.strip()
            if s and not s.startswith('//'):
                if 'main' in s:
                    tac.append("FUNC_BEGIN main")
                elif s == '}':
                    tac.append("FUNC_END")
                elif '=' in s and 'if' not in s:
                    tac.append(f"  {s.rstrip(';')}")
                elif 'for' in s:
                    tac.append("; FOR")
                elif 'while' in s:
                    tac.append("; WHILE")
                elif 'printf' in s:
                    tac.append("; CALL")
                elif 'return' in s:
                    tac.append("; RETURN")

        opt = []
        prev = None
        for x in tac:
            if x != prev:
                opt.append(x)
                prev = x

        removed = len(tac) - len(opt)
        fmt = [{"#": i + 1, "Instruction": x} for i, x in enumerate(opt)]
        return jsonify({"optimized": fmt, "original_count": len(tac), "optimized_count": len(opt), "removed": removed,
                        "error": None}), 200
    except Exception as e:
        return jsonify({"error": str(e), "optimized": [], "removed": 0}), 500


@app.route('/codegen', methods=['POST'])
def codegen():
    try:
        code = request.json.get('source_code', '')
        if not code: return jsonify({"error": "No code", "assembly": [], "assembly_count": 0}), 400

        asm = ["; x86-64 Assembly", ".section .text", ".globl main", "main:", "  PUSH RBP", "  MOV RBP, RSP"]
        for line in code.split('\n'):
            s = line.strip()
            if not s or s.startswith('//') or s.startswith('#'):
                continue
            
            if 'printf' in s:
                asm.append("  CALL printf")
            elif 'scanf' in s:
                asm.append("  CALL scanf")
            elif s == 'return 0;':
                continue
            elif '++' in s:
                var = re.sub(r'[^a-zA-Z0-9_]', '', s.replace('++', ''))
                asm.append(f"  INC DWORD PTR [{var}]")
            elif '--' in s:
                var = re.sub(r'[^a-zA-Z0-9_]', '', s.replace('--', ''))
                asm.append(f"  DEC DWORD PTR [{var}]")
            elif '=' in s and 'if' not in s and 'for' not in s and 'while' not in s:
                s = s.rstrip(';')
                if ',' in s and '=' in s:
                    parts = s.split(',')
                    for p in parts:
                        if '=' in p:
                            p = re.sub(r'^(int|float|char)\s+', '', p.strip())
                            l, r = p.split('=', 1)
                            asm.append(f"  MOV DWORD PTR [{l.strip()}], {r.strip()}")
                else:
                    s = re.sub(r'^(int|float|char)\s+', '', s)
                    if '=' in s:
                        l, r = s.split('=', 1)
                        l, r = l.strip(), r.strip()
                        if '+' in r:
                            op1, op2 = r.split('+')
                            asm.append(f"  MOV EAX, {op1.strip()}")
                            asm.append(f"  ADD EAX, {op2.strip()}")
                            asm.append(f"  MOV DWORD PTR [{l}], EAX")
                        elif '-' in r:
                            op1, op2 = r.split('-')
                            asm.append(f"  MOV EAX, {op1.strip()}")
                            asm.append(f"  SUB EAX, {op2.strip()}")
                            asm.append(f"  MOV DWORD PTR [{l}], EAX")
                        elif '*' in r:
                            op1, op2 = r.split('*')
                            asm.append(f"  MOV EAX, {op1.strip()}")
                            asm.append(f"  IMUL EAX, {op2.strip()}")
                            asm.append(f"  MOV DWORD PTR [{l}], EAX")
                        elif '/' in r:
                            op1, op2 = r.split('/')
                            asm.append(f"  MOV EAX, {op1.strip()}")
                            asm.append(f"  MOV EBX, {op2.strip()}")
                            asm.append(f"  CDQ")
                            asm.append(f"  IDIV EBX")
                            asm.append(f"  MOV DWORD PTR [{l}], EAX")
                        elif '%' in r:
                            op1, op2 = r.split('%')
                            asm.append(f"  MOV EAX, {op1.strip()}")
                            asm.append(f"  MOV EBX, {op2.strip()}")
                            asm.append(f"  CDQ")
                            asm.append(f"  IDIV EBX")
                            asm.append(f"  MOV DWORD PTR [{l}], EDX")
                        else:
                            asm.append(f"  MOV EAX, {r}")
                            asm.append(f"  MOV DWORD PTR [{l}], EAX")
            elif 'if' in s:
                asm.append("; IF Condition Check")
                asm.append("  CMP EAX, EBX")
                asm.append("  JLE .L_ELSE")
            elif 'else' in s:
                asm.append(".L_ELSE:")
            elif 'while' in s:
                asm.append(".L_WHILE_START:")
                asm.append("; While Condition")
                asm.append("  CMP EAX, 0")
                asm.append("  JE .L_WHILE_END")
            elif 'for' in s:
                asm.append("; FOR loop setup")
                asm.append(".L_FOR_START:")
        asm.extend(["  XOR EAX, EAX", "  POP RBP", "  RET"])

        fmt = [{"#": i + 1, "Code": x} for i, x in enumerate(asm)]
        return jsonify({"assembly": fmt, "assembly_count": len(asm), "error": None}), 200
    except Exception as e:
        return jsonify({"error": str(e), "assembly": [], "assembly_count": 0}), 500


if __name__ == '__main__':
    print("=" * 40)
    print(" Backend running on :5000")
    print("=" * 40)
    app.run(host='localhost', port=5000, debug=False, threaded=True)