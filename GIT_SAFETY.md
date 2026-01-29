# Git Safety Guide

Prevent your data from accidentally being uploaded to git.

## How It's Protected

### 1. .gitignore Configuration

The `.gitignore` file prevents your data from being committed:

```
# User data (do not commit)
input/*.csv        ← Your CSV files are ignored
input/.DS_Store

# Generated reports (do not commit)
output/*.json      ← Your reports are ignored
output/*.csv

# Credentials
credentials.json   ← API credentials are ignored
```

Only these are tracked:
- `input/README.md` - Template instructions (NO DATA)
- `output/README.md` - Report documentation (NO DATA)

## Safe Workflow

### ✅ Safe: Test with your data locally

```bash
# Put your CSV files in input/
input/properties.csv      ← Your data here
input/craftsman.csv       ← Your data here

# Run the analyzer
python3 google_sheets_analyzer.py

# Output goes to output/ (also ignored by git)
output/craftsman_coverage_report_20260129_174011.json  ← NOT committed
output/craftsman_coverage_report_20260129_174011.csv   ← NOT committed
```

Your files are safe because they're in `input/*.csv` which is in `.gitignore`.

### ❌ Dangerous: Don't do this

```bash
# ❌ BAD: Never manually add input CSV files
git add input/properties.csv
git add input/craftsman.csv

# ❌ BAD: Never use git add -A with data files
git add -A  # This could accidentally stage your CSV files!

# ❌ BAD: Never commit reports
git add output/*.json
git add output/*.csv
```

## Verification Commands

### Check if files are protected by .gitignore

```bash
# Verify your CSV files are ignored
git check-ignore input/properties.csv
git check-ignore input/craftsman.csv

# Should print:
# .gitignore:24:input/*.csv  input/properties.csv
# .gitignore:24:input/*.csv  input/craftsman.csv
```

### Before committing, verify nothing sensitive is staged

```bash
# Check what's staged for commit
git status

# Should show only code/docs changes, NOT your CSV files or reports

# See detailed staged changes
git diff --cached

# If you see your CSV data here - STOP! Don't commit!
```

### Check what's in git history

```bash
# List all tracked files
git ls-files | grep input
git ls-files | grep output

# Should only show:
# input/README.md
# output/README.md

# NOT any .csv, .json files
```

## Safe Commit Workflow

### Step 1: Make code changes

```bash
nano google_sheets_analyzer.py
```

### Step 2: Verify nothing dangerous is staged

```bash
git status
```

Expected output:
```
Changes not staged for commit:
  modified:   google_sheets_analyzer.py    ← Safe
  modified:   README.md                    ← Safe

Untracked files:
  input/properties.csv                     ← Ignored (not tracked)
  input/craftsman.csv                      ← Ignored (not tracked)
  output/craftsman_coverage_report_*.json  ← Ignored (not tracked)
  output/craftsman_coverage_report_*.csv   ← Ignored (not tracked)
```

### Step 3: Explicitly add only safe files

```bash
# Add specific code files ONLY
git add google_sheets_analyzer.py
git add README.md

# OR add by type
git add *.py
git add *.md
```

### Step 4: Verify staged changes

```bash
git diff --cached

# Should only show code changes, NO CSV data
```

### Step 5: Commit with confidence

```bash
git commit -m "Your commit message"
```

## Emergency: If Data Was Accidentally Staged

```bash
# STOP - don't commit!
# Unstage everything
git reset

# Verify it's unstaged
git status

# Now proceed with safe workflow above
```

## Git Hooks for Extra Protection

If you want automatic protection, create `.git/hooks/pre-commit`:

```bash
#!/bin/bash
# Prevent committing CSV files and reports

if git diff --cached --name-only | grep -E '\.csv$|\.json$|credentials\.json'; then
    echo "❌ ERROR: Attempting to commit data files!"
    echo "These files are protected by .gitignore:"
    git diff --cached --name-only | grep -E '\.csv$|\.json$|credentials\.json'
    exit 1
fi

exit 0
```

Make it executable:
```bash
chmod +x .git/hooks/pre-commit
```

## Troubleshooting

### "I already committed my data!"

Don't panic. You can remove it from git history:

```bash
# Remove files from git history
git rm --cached input/properties.csv
git rm --cached input/craftsman.csv
git commit -m "Remove accidentally committed data files"

# Add to .gitignore (already done)
echo "input/*.csv" >> .gitignore
git add .gitignore
git commit -m "Ensure CSV files are ignored"
```

### "I'm not sure what's tracked"

```bash
# List all files git tracks
git ls-files

# Look for suspicious .csv, .json, or credentials files
# If you see your data, it was committed
```

## Summary

✅ **Safe to do (won't upload data):**
- Edit code files (*.py)
- Edit documentation (*.md)
- Test with CSV files in `input/` folder
- Generate reports in `output/` folder
- Run `git add` on specific code files

❌ **Never do (will expose data):**
- `git add -A` without checking
- Manually committing CSV files
- Committing `credentials.json`
- Committing files from `output/` folder
- Using `git add input/` or `git add output/`

**Remember: .gitignore protects your files, but only if you don't explicitly force-add them!**
