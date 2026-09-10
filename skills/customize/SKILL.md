---
name: customize
description: >
  Edit the fairness-opinion-legal practice profile: the SEC contact identity,
  precedent window, drafting mode, house style, output formats, gates, or the
  reviewer. Use when the user says "change the default", "turn the shell gate
  off", "switch to procedure mode", "update my profile", or complains that an
  output keeps doing something the profile drives.
argument-hint: "[section name] [new value]"
---

# /customize

1. Read `~/.claude/plugins/config/fairness-opinion-legal/CLAUDE.md`. Show the section the user named (or list the sections).
2. Apply the change, show the diff, confirm, write.
3. If the change is the SEC identity, remind the user it is sent to the SEC with every request and nowhere else.

Sections: Who's using this · EDGAR identity · Precedent defaults · Drafting · Outputs · Gates · Deals · Available integrations.
