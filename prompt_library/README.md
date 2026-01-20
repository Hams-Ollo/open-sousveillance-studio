# Alachua Civic Intelligence Prompt Library

**Version:** 1.0  
**Last Updated:** January 2026  
**Purpose:** AI-assisted civic monitoring prompts for environmental protection and democratic accountability

---

## Overview

This prompt library contains structured prompts designed for copy/paste use with AI systems (Claude, ChatGPT, Gemini). Each prompt is self-contained and produces standardized markdown reports.

## Folder Structure

```
prompt_library/
├── README.md                    # This file
├── config/
│   ├── source-registry.md      # All data source URLs
│   └── geographic-scope.md     # Jurisdiction boundaries
├── layer-1-scouts/             # Daily/Weekly data collection
│   ├── A1-meeting-intelligence-scout.md
│   ├── A2-permit-application-scout.md
│   ├── A3-legislative-code-monitor.md
│   └── A4-entity-relationship-mapper.md
├── layer-2-analysts/           # Weekly analysis
│   ├── B1-impact-assessment-analyst.md
│   └── B2-procedural-integrity-analyst.md
├── layer-3-synthesizers/       # Monthly/Quarterly synthesis
│   ├── C1-public-education-content-generator.md
│   ├── C2-strategic-campaign-planner.md
│   ├── C3-quarterly-democratic-health-scorecard.md
│   └── C4-annual-review-and-forecast.md
├── templates/                  # Output format templates
│   ├── report-output-standard.md
│   ├── newsletter-format.md
│   ├── social-media-templates.md
│   └── public-comment-template.md
└── examples/
    └── sample-outputs.md
```

## How to Use

### Step 1: Choose Your Prompt
Select based on your monitoring need and schedule:

| Prompt | Purpose | Frequency |
|--------|---------|-----------|
| A1 | Meeting monitoring | Daily/2-3x week |
| A2 | Permit tracking | Daily/2-3x week |
| A3 | Legislative changes | Weekly |
| A4 | Entity relationships | As needed |
| B1 | Impact assessment | Weekly |
| B2 | Procedural integrity | Weekly |
| C1 | Public content | Monthly |
| C2 | Campaign planning | Monthly |
| C3 | Health scorecard | Quarterly |
| C4 | Annual review | Annually |

### Step 2: Copy the Prompt
Open the prompt file and copy the entire contents (everything between `--- PROMPT START ---` and `--- PROMPT END ---`).

### Step 3: Paste into AI System
Works with:
- **Claude** (recommended) — Sonnet or Opus
- **ChatGPT** — GPT-4 or GPT-4o
- **Gemini** — Gemini Pro or Ultra

### Step 4: Save the Output
Save the AI's response to the appropriate folder:
```
data/
├── daily/YYYY-MM-DD-A1-meetings.md
├── weekly/YYYY-WXX-B1-impact-assessment.md
├── monthly/YYYY-MM-C1-public-content.md
├── quarterly/YYYY-QX-C3-health-scorecard.md
└── annual/YYYY-C4-annual-review.md
```

## Output Naming Convention

`YYYY-MM-DD-[AGENT]-[topic].md`

Examples:
- `2026-01-20-A1-city-commission.md`
- `2026-01-20-A2-tara-permits.md`
- `2026-W03-B1-impact-assessment.md`
- `2026-01-C1-newsletter-content.md`

## Key Entities (Quick Reference)

### Primary Threat
- **Tara April LLC** — 580 acres, 1000+ units over Mill Creek Sink
- **Mill Creek Sink** — 12-day travel time to Hornsby Spring (dye trace proven)

### Key Officials/Entities
- City of Alachua Commission
- Justin Tabor (former Planning Director, now with developer's firm)
- Bryan Buescher / Our Alachua Water (coalition partner)

### Critical Legal Framework
- Florida Sunshine Law (F.S. 286.011)
- Public Records Law (F.S. Chapter 119)
- Comprehensive Planning Law (F.S. Chapter 163)

## Tips for Best Results

1. **Be patient** — Let the AI complete its full analysis
2. **Verify sources** — Always check AI outputs against primary documents
3. **Iterate** — If output is incomplete, ask follow-up questions
4. **Document gaps** — Note when information is unavailable for records requests

## Troubleshooting

| Issue | Solution |
|-------|----------|
| AI can't access URLs | Copy/paste document content into prompt |
| Output too long | Add "Be concise, top 3 priorities only" |
| Output too technical | Use C1 synthesizer to translate |
| Missing information | Note for public records request |

---

*For full project context, see `/docs/PROJECT-KNOWLEDGE-BASE.md`*
