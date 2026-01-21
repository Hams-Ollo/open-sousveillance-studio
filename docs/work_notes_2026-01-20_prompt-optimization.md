# Work Notes: Prompt Library Optimization

**Date:** 2026-01-20  
**Author:** ZenBot (AI Development Assistant)  
**Task:** Comprehensive prompt library optimization for reliability, accuracy, and pipeline integration

---

## Executive Summary

Completed a comprehensive optimization of all 10 prompts in the Alachua Civic Intelligence System prompt library. Changes focused on:

1. **Reliability Engineering** - Added hallucination prevention, error handling, and verification checklists
2. **Platform Optimization** - Tailored prompts for Gemini (Layer 1) and Claude (Layer 2-3)
3. **Pipeline Integration** - Enhanced YAML frontmatter and artifact output instructions for data pipeline ingestion
4. **Behavioral Constraints** - Added core identity blocks to improve consistency and prevent fabrication
5. **Chain-of-Thought Guidance** - Added reasoning process sections to improve accuracy

---

## Files Created

### New Configuration Files

| File | Purpose |
|------|---------|
| `prompt_library/config/alachua-context.md` | Shared context block with Tara portfolio, entities, legal framework - update once, propagate everywhere |
| `prompt_library/config/agent-behavioral-standards.md` | Standardized behavioral constraints, error handling, verification checklists, platform instructions |

---

## Files Modified

### Layer 1 Scout Prompts (Gemini-optimized)

| File | Key Changes |
|------|-------------|
| `A1-meeting-intelligence-scout.md` | Added: Core Identity, Reasoning Process, Gemini-specific source verification, enhanced YAML frontmatter, Verification Checklist, Error Handling, Confidence Assessment, artifact output instructions |
| `A2-permit-application-scout.md` | Added: Core Identity, Reasoning Process, Gemini-specific instructions, enhanced frontmatter, Verification Checklist, Error Handling, Confidence Assessment |
| `A3-legislative-code-monitor.md` | Added: Core Identity, full Tara/Tabor context, Reasoning Process, enhanced frontmatter, Verification Checklist, Error Handling |
| `A4-entity-relationship-mapper.md` | Added: Core Identity, corrected Tabor timeline (early 2025 not Oct 2024), full entity context, Reasoning Process, enhanced frontmatter, Verification Checklist |

### Layer 2 Analyst Prompts (Claude-optimized)

| File | Key Changes |
|------|-------------|
| `B1-impact-assessment-analyst.md` | Added: Core Identity, Claude-specific input validation, Reasoning Process, enhanced frontmatter with `inputs_validated` field, Verification Checklist, Error Handling, input pasting instructions |
| `B2-procedural-integrity-analyst.md` | Added: Core Identity, Claude-specific input validation, Reasoning Process, enhanced frontmatter, Verification Checklist, Error Handling, input pasting instructions |

### Layer 3 Synthesizer Prompts (Claude-optimized)

| File | Key Changes |
|------|-------------|
| `C1-public-education-content-generator.md` | Added: Core Identity, Claude-specific input validation, Reasoning Process, enhanced frontmatter, Verification Checklist, Error Handling |
| `C2-strategic-campaign-planner.md` | Added: Core Identity, Reasoning Process, enhanced frontmatter, Verification Checklist, Error Handling |
| `C3-quarterly-democratic-health-scorecard.md` | Added: Core Identity, Reasoning Process, enhanced frontmatter with `overall_score` and `overall_grade`, Verification Checklist, Error Handling |
| `C4-annual-review-and-forecast.md` | Added: Core Identity, Reasoning Process, enhanced frontmatter, Verification Checklist, Error Handling |

---

## Detailed Changes by Category

### 1. Core Identity Blocks

Added to all 10 prompts. Example structure:

```markdown
### CORE IDENTITY

You are a meticulous, accuracy-obsessed civic intelligence agent...

**You ALWAYS:**
- Cite sources for every factual claim
- Distinguish facts from inferences (label inferences explicitly)
- Flag uncertainty when confidence is below HIGH
- Prioritize actionable information

**You NEVER:**
- Fabricate meeting dates, times, vote counts, names, or URLs
- Assume information not explicitly stated in sources
- Editorialize or express political opinions
- Skip verification to appear more comprehensive
```

### 2. Reasoning Process (Chain-of-Thought)

Added structured reasoning steps to all prompts. Example:

```markdown
### REASONING PROCESS

Before generating your report, work through these steps:

**Step 1: Data Gathering**
- Search each primary source for upcoming meetings
- Note any sources that are unavailable or outdated

**Step 2: Relevance Filtering**
- Scan all agenda items for priority keywords
- Flag any Tara-related items immediately

**Step 3: Temporal Verification**
- Confirm all meeting dates are in the future (for upcoming)
...
```

### 3. Enhanced YAML Frontmatter

Standardized frontmatter schema for pipeline ingestion:

```yaml
---
report_id: A1-[YYYY]-[MM]-[DD]-001
report_type: meeting-intelligence
agent: A1-meeting-intelligence-scout
date_generated: [YYYY-MM-DD]
period_covered: [YYYY-MM-DD] to [YYYY-MM-DD]
jurisdiction: City of Alachua, Alachua County
urgency_level: [RED|YELLOW|GREEN]
confidence_level: [HIGH|MEDIUM|LOW]
data_quality: [COMPLETE|PARTIAL|INCOMPLETE]
sources_consulted: [NUMBER]
pipeline_ready: true
---
```

### 4. Verification Checklists

Added pre-submission verification to all prompts:

```markdown
### VERIFICATION CHECKLIST

Before finalizing your report, verify:

- [ ] All dates are temporally correct (future for upcoming, past for recent)
- [ ] All URLs are properly formatted and were verified as live
- [ ] All vote counts add up correctly (yes + no + abstain = total)
- [ ] No placeholder text remains (no unexplained [brackets])
- [ ] Executive Summary accurately reflects report contents
- [ ] All RED alerts have specific deadlines and actions
- [ ] Sources table lists all sources actually consulted
- [ ] Confidence levels assigned to each major section
```

### 5. Error Handling

Added graceful degradation instructions:

```markdown
### ERROR HANDLING

**If a source is unavailable:**
1. Document: `"Source unavailable: [URL] returned [error] as of [datetime]"`
2. Attempt archive.org or cached version
3. Note in Information Gaps section
4. Reduce confidence level for affected sections

**If information conflicts:**
1. Present both versions with sources
2. Note: `"CONFLICT: Source A reports [X] while Source B reports [Y]"`
3. Flag for manual verification

**If critical data is missing:**
1. Set `data_quality: PARTIAL` in frontmatter
2. Add warning in Executive Summary
3. Specify what's needed to complete the report
```

### 6. Platform-Specific Instructions

**Layer 1 (Gemini):**
- Source verification using `site:` searches
- URL verification before citing
- Archive.org fallback
- Cross-reference across multiple sources

**Layer 2-3 (Claude):**
- Input validation for pasted reports
- YAML frontmatter parsing
- Contradiction detection between input reports
- Input pasting format instructions

### 7. Confidence Assessment

Added structured confidence reporting:

```markdown
## Confidence Assessment

**Overall Report Confidence:** [HIGH|MEDIUM|LOW]

**Confidence by Section:**
| Section | Confidence | Rationale |
|---------|------------|-----------|
| Upcoming Meetings | | |
| Recent Actions | | |
| Tara Tracker | | |
```

### 8. Artifact Output Instructions

Added explicit instructions for markdown artifact generation:

```markdown
**IMPORTANT:** Generate your complete report as a **markdown artifact** that can be saved directly as a `.md` file. The artifact must be self-contained with all frontmatter and formatting.
```

### 9. Usage Notes Updates

Enhanced usage notes with:
- Platform recommendation (Gemini or Claude)
- Input pasting format for Claude prompts
- Artifact handling instructions
- Quality control checklist

---

## Version Updates

All prompts updated to:
- **Version:** 2.0.0
- **Last Updated:** 2026-01-20

---

## Context Corrections

### Justin Tabor Timeline
- **Corrected:** Resigned "early 2025" (not "October 2024" as previously stated in A4)
- Updated in A4-entity-relationship-mapper.md

---

## Recommended Workflow

### For Layer 1 Scouts (Gemini Deep Research)
1. Copy prompt from `prompt_library/layer-1-scouts/`
2. Paste into Gemini Deep Research
3. Gemini will search web sources and generate report
4. Copy generated markdown artifact
5. Save to `data/daily/` or `data/weekly/` as appropriate

### For Layer 2-3 Analysts/Synthesizers (Claude)
1. Copy prompt from `prompt_library/layer-2-analysts/` or `layer-3-synthesizers/`
2. Paste into Claude
3. Add input reports after prompt using separator format:
   ```
   ---
   ## INPUT: A1 Meeting Intelligence Report
   [Paste report here]
   ```
4. Claude will synthesize and generate report
5. Copy generated markdown artifact
6. Save to appropriate `data/` subfolder

---

## Pipeline Integration

Reports are now structured for automated processing:

1. **YAML Frontmatter** - Machine-readable metadata
2. **Consistent Headers** - Extractable sections
3. **Markdown Tables** - Parseable data
4. **Pipeline Ready Flag** - `pipeline_ready: true` in frontmatter

---

## Next Steps (Recommended)

1. **Test prompts** - Run each prompt through its target platform
2. **Validate pipeline** - Ensure data pipeline can parse new frontmatter schema
3. **Create automation** - Consider scripts to automate report saving and ingestion
4. **Monitor quality** - Track confidence levels and data quality across reports
5. **Iterate** - Refine prompts based on actual output quality

---

## Files Summary

| Category | Files Modified | Files Created |
|----------|---------------|---------------|
| Config | 0 | 2 |
| Layer 1 Scouts | 4 | 0 |
| Layer 2 Analysts | 2 | 0 |
| Layer 3 Synthesizers | 4 | 0 |
| Documentation | 0 | 1 |
| **Total** | **10** | **3** |

---

*Work notes generated by ZenBot*  
*Alachua Civic Intelligence Reporting Studio*
