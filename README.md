# ⚙️ Compiler Phases Project

> A full-stack web application that demonstrates all **4 phases of a Compiler** on C source code — built with Python, Flask, and Streamlit.

---

## 👥 Team Members

| Name | Register Number |
|------|----------------|
| Shreyans Modi | RA2311026010720 |
| Roshan | RA2311026010713 |
| Lokesh | RA2311026010715 |
| Uthkarsh | RA2311026010725 |

> **Subject:** Compiler Design — SRM Institute of Science & Technology

---

## 📌 About the Project

This project implements the **4 major phases of a compiler** for C language source code through an interactive web interface. Users can input any C program and analyse it through each phase step by step.

---

## 🔄 Compiler Phases Implemented

### Phase 1 — Tokenization (Lexical Analysis)
- Breaks source code into tokens
- Identifies: `KEYWORD`, `IDENTIFIER`, `INTEGER`, `FLOAT`, `STRING`, `OPERATOR`, `DELIMITER`, `PREPROCESSOR`
- Colour-coded token stream display
- Token table with **Line**, **Token Type**, **Lexeme**
- Detects unknown/invalid characters as lexical errors

### Phase 2 — Syntax Analysis (Parsing)
- Checks grammar and structure of the C code
- Detects mismatched brackets `{}`, `()`, `[]`
- Detects missing semicolons
- Builds and displays an **Abstract Syntax Tree (AST)**
- Reports exact line number of syntax errors

### Phase 3 — Semantic Analysis
- Checks the meaning and correctness of the code
- Detects undeclared variables
- Detects unused variables (warnings)
- Builds a complete **Symbol Table** (Name, Kind, Type, Line, Used)
- Reports semantic errors and warnings separately

### Phase 4 — Intermediate Code Generation
- Generates **Three Address Code (TAC)**
- Handles: assignments, arithmetic, `if/else`, `for`, `while`, `printf/scanf`, `return`
- Displays numbered instruction table
- Code view for easy reading

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Python — Streamlit |
| Backend | Python — Flask |
| Database | SQLite |
| Language Supported | C |

---

## 📁 Project Structure

```
Compiler-Phases-Project/
│
├── backend/
│   ├── app.py          # Flask API — all 4 compiler phases
│   └── compiler.db     # SQLite database (auto-created)
│
├── frontend/
│   ├── app.py          # Streamlit UI — 4-phase selector
│
├── requirements.txt
└── README.md
```

---

## ⚙️ Setup & Run

### Prerequisites
- Python 3.8+
- pip

### Step 1 — Clone the Repository
```bash
git clone https://github.com/YOUR_USERNAME/Compiler-Phases-Project.git
cd Compiler-Phases-Project
```

### Step 2 — Install Backend Dependencies
```bash
cd backend
pip install flask flask-cors
```

### Step 3 — Start the Backend
```bash
python app.py
```
Backend runs at: `http://localhost:5000`

### Step 4 — Install Frontend Dependencies
```bash
cd frontend
pip install streamlit requests pandas
```

### Step 5 — Start the Frontend
```bash
streamlit run app.py
```
Frontend runs at: `http://localhost:8501`

---

## 🖥️ API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/tokenize` | Phase 1 — Tokenize source code |
| POST | `/syntax` | Phase 2 — Syntax analysis + AST |
| POST | `/semantic` | Phase 3 — Semantic analysis |
| POST | `/codegen` | Phase 4 — Generate TAC |
| GET | `/health` | Health check |

---

## 📸 Sample Output

### Input Code
```c
#include <stdio.h>
int main() {
    int i = 1;
    while(i <= 5) {
        printf("Value: %d\n", i);
        i++;
    }
    return 0;
}
```

### Phase 1 — Token Table
| Line | Token Type | Lexeme |
|------|-----------|--------|
| 1 | PREPROCESSOR | #include <stdio.h> |
| 2 | KEYWORD | int |
| 2 | IDENTIFIER | main |
| 3 | KEYWORD | int |
| 3 | IDENTIFIER | i |
| 3 | OPERATOR | = |
| 3 | INTEGER | 1 |

### Phase 4 — Three Address Code
```
FUNC_BEGIN main
  DECLARE int i
  i = 1
L1:
  t1 = i <= 5
  IF_FALSE t1 GOTO L2
  CALL printf [...]
  t2 = i + 1
  i = t2
  GOTO L1
L2:
  RETURN 0
FUNC_END
```

---

## 🔍 Error Detection Examples

| Phase | Error Type | Example |
|-------|-----------|---------|
| Lexical | Unknown character | `@` or `$` in code |
| Syntax | Missing semicolon | `int x = 5` without `;` |
| Syntax | Unmatched bracket | `{` without closing `}` |
| Semantic | Undeclared variable | Using `x` without `int x;` |
| Semantic | Unused variable | Declaring `int y;` but never using it |

---

## 📄 License
This project is built for academic purposes under the Compiler Design course at SRM Institute of Science & Technology.
