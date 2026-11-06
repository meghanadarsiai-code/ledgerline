# PROMPTS.md

## Entry 1 - 6 Nov 2026
**What I asked:** Commands to set up Git and a .gitignore on Windows Command Prompt.
**What the tool produced:** `echo db.sqlite3>> .gitignore`
**What was wrong:** In Windows cmd, a digit right before `>>` is read as a file handle number, so that line would not have been written to .gitignore.
**Who caught it:** The AI noticed in its next message, before I ran the command. I did not catch it myself.
**What I did instead:** Put the redirect first (`>> .gitignore echo db.sqlite3`) and checked the result with `type .gitignore`.
**Commit:** https://github.com/meghanadarsiai-code/ledgerline/commit/0722504