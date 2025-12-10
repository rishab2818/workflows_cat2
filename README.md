# workflows_cat2
python script.py samples
Ada Identifier Normalizer

This tool scans Ada .ada source files and enforces strict identifier casing rules for variables, constants, and types using deterministic heuristics.

It is designed for large Ada codebases (avionics / safety-critical style) where:

files are processed independently,

package specs or bodies may not be locally available,

naming consistency is mandatory.

✅ Original files are never modified
✅ Corrected files are written to a separate output directory

What this tool does

Scans .ada files in a directory (one file at a time)

Determines whether a file is:

a package spec/body, or

a standalone procedure/function

Applies consistent casing rules to:

variables

constants

types (including built-in types)

Rewrites the file with corrected casing

Saves the result in _normalized/

Naming Rules Enforced
1. Types (ALWAYS GLOBAL)

All type names are always converted to UPPERCASE.

This includes:

type and subtype names

Built-in types (Integer, Float, etc.)

Types used in:

variable declarations

parameter lists

array definitions (array … of)

function return types

Example:

Index : Integer;


Becomes:

index : INTEGER;

2. Constants

All constants are converted to UPPERCASE.

Detected by:

Rate : constant Float := 1.5;


Becomes:

RATE : constant FLOAT := 1.5;


Applies to:

package files

standalone procedures/functions

3. Package specification / package body files

A file is treated as a package unit if the first meaningful keyword is:

package


In package files:

Variables → UPPERCASE

Constants → UPPERCASE

Types → UPPERCASE

All usages rewritten consistently

Reason:
Everything in a package is global.

4. Standalone procedure / function files

A file is treated as standalone if it contains:

procedure
or
function

a) Global variables (explicit)

Declarations before the subprogram are treated as global:

Global_Count : Integer := 0;

procedure Process is


Becomes:

GLOBAL_COUNT : INTEGER := 0;

b) Parameters

Parameter names → lowercase

Parameter types → UPPERCASE

Example:

procedure P (Count : in Integer);


Becomes:

procedure P (count : in INTEGER);

c) Local variables

Variables declared between is and begin:

Index : Integer := 1;


Becomes:

index : INTEGER := 1;

d) Loop variables

Loop index variables are treated as local:

for I in Some_Type loop


Becomes:

for i in SOME_TYPE loop

5. External global variables (implicit detection)

If an identifier:

appears on the left-hand side of :=

is not declared as:

a parameter

a local variable

a constant

a type

Then it is assumed to be a global variable from another unit.

Such identifiers are converted to UPPERCASE.

Example:

Global_Count := Global_Count + index;


Becomes:

GLOBAL_COUNT := GLOBAL_COUNT + index;


This allows correct handling even when the defining package or spec is missing.

Scope Detection Logic (Important)

This tool does not use a full Ada parser.
It relies on safe, deterministic heuristics:

Location	Interpreted as
Declaration before procedure/function	Global
Procedure parameters	Local
Between is and begin	Local
for X in ... loop variable	Local
LHS of := and not declared	Global
Type / subtype	Always global

This makes the behavior:

predictable

auditable

easy to maintain

How to Run

From the directory containing process.py:

On sample files
python process.py samples

On your own Ada source directory
python process.py D:\my_project\ada_src

Custom output directory
python process.py D:\ada_src --out-dir D:\ada_fixed


Output is written to:

<source_dir>/_normalized/

What this tool does NOT do

By design, it does not:

Reformat indentation or spacing

Rearrange logic

Perform semantic validation

Resolve cross-file symbols

Parse generics or instantiations deeply

Depend on GNAT / compiler APIs

This keeps it safe, fast, and predictable.

Intended Use Cases

Enforcing Ada naming conventions

Cleaning legacy Ada code

Pre-commit normalization

Safety-critical / avionics codebases

Offline analysis where specs may be missing

Future Extensions (Optional)

The script is structured so it can be extended to add:

Dry-run / check-only mode

Diff generation

JSON violation reports

Coding-rule enforcement (DAL / MISRA-style)

Pre-commit hook integration

Summary

This is a practical engineering tool, not a cosmetic formatter.

It reflects how real Ada codebases work:

files in isolation,

strict naming rules,

incomplete symbol visibility.

If something violates the rule, the tool corrects it deterministically.
