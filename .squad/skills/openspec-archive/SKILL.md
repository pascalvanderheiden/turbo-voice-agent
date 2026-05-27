# Skill: Archiving OpenSpec Changes

**Owner**: Redfoot (Spec Manager)  
**Context**: Finalizing completed OpenSpec changes and integrating spec deltas into the project library  
**Applies to**: All completed OpenSpec changes (proposal → explore → implement → archive workflow)

## When to Use

After implementation of an OpenSpec change is verified complete and production-ready:

1. Update the change's `tasks.md` checklist to accurately reflect final state
2. Add a "Post-Implementation Notes" section to `proposal.md` documenting delivery
3. Archive the change to `openspec/changes/archive/{date}-{change-name}/`
4. Merge spec deltas from the change into `openspec/specs/` (canonical library)
5. Commit and push

## Pattern

### 1. Verify & Document Completion

**In tasks.md:**
- Walk every task and mark [x] if truly complete
- For any unchecked tasks, decide: are they optional/deferred, or blockers?
  - If optional: annotate with _(optional; deferred as post-migration utility)_
  - If blocking: do not archive yet — document why

**In proposal.md, add a new section:**
```markdown
## Post-Implementation Notes

### Delivery Summary

- **Infrastructure**: [what shipped]
- **Backend**: [what shipped]
- **Testing**: [results]
- **Deployment**: [verification]
- **Docs**: [updates]

### Optional Tasks (Not Shipped)

- **Task X.Y**: [reason]

### Divergences from Proposal

[List any deviations from original spec, or "None"]
```

### 2. Validate the Change

```bash
openspec validate {change-name} --strict
# Expected: "Change '{change-name}' is valid"
# If errors: fix before archiving
# If warnings about incomplete tasks: confirm are optional, proceed with -y
```

### 3. Archive

**Option A: CLI (if available)**
```bash
openspec archive {change-name}
# Automatically moves to archive/{date}-{change-name}/ and merges specs
```

**Option B: Manual (if CLI hangs or unavailable)**

```bash
# Create archive destination
mkdir -p openspec/changes/archive/$(date -u +%Y-%m-%d)-{change-name}

# Copy all change artifacts
cp -r openspec/changes/{change-name}/* openspec/changes/archive/$(date -u +%Y-%m-%d)-{change-name}/

# Merge spec deltas
for spec in $(ls -1 openspec/changes/archive/$(date -u +%Y-%m-%d)-{change-name}/specs/); do
  if [ -f "openspec/specs/$spec/spec.md" ]; then
    # Append delta to existing spec (preserves history)
    cat openspec/changes/archive/$(date -u +%Y-%m-%d)-{change-name}/specs/$spec/spec.md >> openspec/specs/$spec/spec.md
  else
    # Create new spec (e.g., for new capabilities)
    mkdir -p openspec/specs/$spec
    cp openspec/changes/archive/$(date -u +%Y-%m-%d)-{change-name}/specs/$spec/spec.md openspec/specs/$spec/spec.md
  fi
done

# Clean up original change directory
rm -rf openspec/changes/{change-name}
```

### 4. Commit

```bash
git add openspec/
git commit -m "docs(openspec): archive {change-name}; [summary of status]

{change-name}: all tasks complete, deployed & verified
  - [key achievement 1]
  - [key achievement 2]
  - [optional tasks deferred: task X.Y reason, task Z.W reason]
  - Spec deltas merged into openspec/specs/ ({spec1}, {spec2})

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"

git push origin main
```

## Pro Tips

1. **Don't edit specs mid-implementation**: Keep `openspec/specs/` as read-only until archive. This preserves the spec library as the single source of truth. During development, all changes stay in the change's local `specs/` delta directory.

2. **Merge, don't replace**: When merging a delta into an existing spec, append it to preserve both the original requirements and the delta details. This creates a historical record and helps trace evolution.

3. **Archive directory naming**: Use `{date}-{change-name}` format (e.g., `2026-05-27-sandbox-dynamic-sessions`). The date helps with sorting and temporal correlation to commits.

4. **Post-impl notes are key**: These capture decisions made during implementation, workarounds, and deviations from the original proposal. Future maintainers rely on this narrative.

5. **Incomplete tasks are OK**: Archive even with 1–2 deferred tasks as long as they're clearly marked optional. Use the "Divergences from Proposal" section to note why.

## Example

After archiving `sandbox-dynamic-sessions`:

```
openspec/changes/archive/2026-05-27-sandbox-dynamic-sessions/  ← historical snapshot
openspec/specs/dynamic-session-sandbox/spec.md                 ← new capability, merged from delta
openspec/specs/aci-sandbox-infra/spec.md                        ← existing spec, delta appended
openspec/specs/aci-sandbox-lifecycle/spec.md                    ← existing spec, delta appended
```

All changes now live in the library; the change directory becomes a reference archive.
