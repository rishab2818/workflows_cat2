# Ada Identifier Normalizer

This tool scans Ada `.ada` source files and **enforces strict identifier casing rules** for variables, constants, and types using deterministic heuristics.

It is designed for **large Ada codebases** (avionics / safety-critical style) where:
- files are processed independently,
- package specs or bodies may not be locally available,
- naming consistency is mandatory.

✅ Original files are **never modified**  
✅ Corrected files are written to a separate output directory  

---

## What this tool does

- Scans `.ada` files in a directory (one file at a time)
- Determines whether a file is:
  - a **package spec/body**, or  
  - a **standalone procedure/function**
- Applies consistent casing rules to:
  - variables
  - constants
  - types (including built-in types)
- Rewrites the file with corrected casing
- Saves the result in `_normalized/`

---

## Naming Rules Enforced

### 1. Types (ALWAYS GLOBAL)

**All type names are always converted to `UPPERCASE`.**

This includes:
- `type` and `subtype` names
- Built-in types (`Integer`, `Float`, etc.)
- Types used in:
  - variable declarations
  - parameter lists
  - array definitions (`array … of`)
  - function return types

Example:

```ada
Index : Integer;
```

Becomes:

```ada
index : INTEGER;
```

---

### 2. Constants

**All constants are converted to `UPPERCASE`.**

Detected by:

```ada
Rate : constant Float := 1.5;
```

Becomes:

```ada
RATE : constant FLOAT := 1.5;
```

---

### 3. Package specification / package body files

A file is treated as a **package unit** if the first meaningful keyword is:

```
package
```

In package files:
- Variables → `UPPERCASE`
- Constants → `UPPERCASE`
- Types → `UPPERCASE`
- All usages rewritten consistently

Reason: **Everything in a package is global.**

---

### 4. Standalone procedure / function files

A file is treated as standalone if it contains:

```
procedure
or
function
```

#### a) Global variables (explicit)

Declarations *before* the subprogram are treated as global:

```ada
Global_Count : Integer := 0;

procedure Process is
```

Becomes:

```ada
GLOBAL_COUNT : INTEGER := 0;
```

---

#### b) Parameters

- Parameter names → `lowercase`
- Parameter types → `UPPERCASE`

```ada
procedure P (Count : in Integer);
```

Becomes:

```ada
procedure P (count : in INTEGER);
```

---

#### c) Local variables

Variables declared between `is` and `begin`:

```ada
Index : Integer := 1;
```

Becomes:

```ada
index : INTEGER := 1;
```

---

#### d) Loop variables

```ada
for I in Some_Type loop
```

Becomes:

```ada
for i in SOME_TYPE loop
```

---

### 5. External global variables (implicit detection)

If an identifier:
- appears on the **left-hand side of `:=`**
- is **not** declared locally or as a parameter/constant/type

It is assumed to be a **global variable from another unit** and converted to `UPPERCASE`.

```ada
Global_Count := Global_Count + index;
```

Becomes:

```ada
GLOBAL_COUNT := GLOBAL_COUNT + index;
```

---

## Scope Detection Logic

| Location | Interpreted as |
|--------|----------------|
Declaration before procedure/function | Global |
Procedure parameters | Local |
Between `is` and `begin` | Local |
Loop variable (`for X in`) | Local |
LHS of `:=` (undeclared) | Global |
Type / subtype | Always global |

---

## How to Run

```bash
python process.py <source_dir>
```

Example:

```bash
python process.py samples
```

Custom output directory:

```bash
python process.py samples --out-dir fixed_samples
```

Output:

```
<source_dir>/_normalized/
```

---

## What this tool does NOT do

- Does not reformat code
- Does not resolve cross-file symbols
- Does not require GNAT or compiler APIs
- Does not change logic

---

## Intended Use Cases

- Ada naming standard enforcement
- Legacy code cleanup
- Pre-commit normalization
- Safety-critical codebases

---

## Summary

This is a **practical engineering tool**, focused on deterministic, safe normalization of Ada identifiers when files are processed independently.
