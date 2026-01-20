# Alachua Civic Intelligence System

**Version:** 1.0  
**Date:** January 2026  
**Location:** City of Alachua, Alachua County, Florida, USA  
**Primary Use Case:** Environmental Protection & Democratic Accountability Monitoring

---

## Mission

This prompt library empowers citizens to monitor, understand, and participate in their democratic institutions through AI-assisted research, analysis, and communication.

Grounded in universal reverence for life and environmental stewardship—not partisan divisions—this system transforms publicly available government data into accessible, actionable intelligence for community members.

> *"Understanding systems is the path to freedom."*

---

## Overview

The Alachua Civic Intelligence System is a collection of structured AI prompts designed to:

1. **Scout** — Continuously scan government sources for new information, meetings, permits, and decisions
2. **Analyze** — Process raw data into meaningful insights, patterns, and compliance assessments
3. **Synthesize** — Generate accessible reports, public education content, and strategic campaign plans
4. **Act** — Empower citizens with specific next steps, deadlines, and participation opportunities

Inspired by the Mill Creek Sink / Tara development case, this system enables citizens to detect threats early, document violations systematically, and coordinate effective advocacy campaigns.

---

## System Architecture

### Three-Layer Agent Framework

```
┌─────────────────────────────────────────────────────────────────────┐
│  LAYER 1: SCOUTS (Daily/Weekly)                                     │
│  Data collection agents monitoring specific sources                 │
│  Output: Raw intelligence reports                                   │
├─────────────────────────────────────────────────────────────────────┤
│  LAYER 2: ANALYSTS (Weekly)                                         │
│  Process scout data for deeper insights and pattern recognition     │
│  Output: Strategic intelligence reports                             │
├─────────────────────────────────────────────────────────────────────┤
│  LAYER 3: SYNTHESIZERS (Monthly/Quarterly/Annual)                   │
│  Aggregate intelligence for public education and campaign planning  │
│  Output: Public-facing content and advocacy strategies              │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Folder Structure

```
alachua-civic-intelligence/
│
├── README.md                           # This document
│
├── config/
│   ├── source-registry.md              # Master list of all data sources with URLs
│   └── geographic-scope.md             # Jurisdiction boundaries and focus areas
│
├── layer-1-scouts/
│   ├── A1-meeting-intelligence-scout.md
│   ├── A2-permit-application-scout.md
│   ├── A3-legislative-code-monitor.md
│   └── A4-entity-relationship-mapper.md
│
├── layer-2-analysts/
│   ├── B1-impact-assessment-analyst.md
│   └── B2-procedural-integrity-analyst.md
│
├── layer-3-synthesizers/
│   ├── C1-public-education-content-generator.md
│   ├── C2-strategic-campaign-planner.md
│   ├── C3-quarterly-democratic-health-scorecard.md
│   └── C4-annual-review-and-forecast.md
│
├── templates/
│   ├── report-output-standard.md       # Standard markdown report format
│   ├── newsletter-format.md            # Weekly/monthly newsletter template
│   ├── social-media-templates.md       # Platform-specific post formats
│   └── public-comment-template.md      # Template for official public comments
│
└── outputs/                            # Where generated reports are saved
    ├── daily/
    ├── weekly/
    ├── monthly/
    ├── quarterly/
    └── annual/
```

---

## The Prompts

### Layer 1: Scouts (Data Collection)

| Prompt | Purpose | Schedule | Key Sources |
|--------|---------|----------|-------------|
| **A1: Meeting Intelligence Scout** | Track upcoming/recent public meetings, agendas, votes | Daily or 2-3x/week | City/County meeting portals, agendas, minutes |
| **A2: Permit & Application Scout** | Monitor development permits and environmental applications | Daily or 2-3x/week | City/County development portals, WMD, DEP |
| **A3: Legislative & Code Monitor** | Track changes to laws, codes, comprehensive plans | Weekly or when ordinances proposed | Municipal codes, state legislature, comp plan amendments |
| **A4: Entity & Relationship Mapper** | Document connections between developers, officials, consultants | Weekly or as needed | Campaign finance, Sunbiz, property records, LinkedIn |

### Layer 2: Analysts (Strategic Intelligence)

| Prompt | Purpose | Schedule | Input |
|--------|---------|----------|-------|
| **B1: Impact Assessment Analyst** | Synthesize cumulative environmental and community impacts | Weekly (Monday) | All scout reports from previous week |
| **B2: Procedural Integrity Analyst** | Monitor democratic processes, transparency, Sunshine Law compliance | Weekly | Meeting records, procedural documentation |

### Layer 3: Synthesizers (Public Output & Strategy)

| Prompt | Purpose | Schedule | Output |
|--------|---------|----------|--------|
| **C1: Public Education Content Generator** | Translate intelligence into accessible public content | Monthly | Newsletter articles, social threads, talking points, FAQs |
| **C2: Strategic Campaign Planner** | Develop tactical advocacy campaigns | Monthly | Campaign plans with timelines, stakeholder analysis, resource allocation |
| **C3: Democratic Health Scorecard** | Assess cumulative state of local democratic accountability | Quarterly | Comprehensive assessment with metrics and trend analysis |
| **C4: Annual Review & Forecast** | Year-in-review and forward-looking analysis | Annually | Full year synthesis, pattern identification, strategic recommendations |

---

## Quick Start

### Step 1: Choose Your Entry Point

**Minimum Viable Monitoring (30 min/day):**
- Run A1 (meetings) and A2 (permits) daily
- Flag urgent items for immediate attention

**Standard Monitoring (5-8 hrs/week):**
- Daily: A1 + A2
- Weekly: A3 + A4 + B1 + B2
- Monthly: C1 + C2

**Full System (10-15 hrs/week):**
- All of the above, plus quarterly C3 and annual C4
- Active content publishing and campaign execution

### Step 2: How to Use a Prompt

1. Open the prompt file (e.g., `A1-meeting-intelligence-scout.md`)
2. Copy the entire prompt text
3. Paste into your AI system (Claude recommended)
4. AI executes research and generates formatted markdown report
5. Save output to appropriate `/outputs/` subfolder
6. Repeat on schedule

### Step 3: Output Organization

Save outputs with date-stamped filenames:

```
outputs/
├── daily/
│   ├── 2026-01-20-A1-meetings.md
│   ├── 2026-01-20-A2-permits.md
│   └── ...
├── weekly/
│   ├── 2026-W03-B1-impact-assessment.md
│   ├── 2026-W03-B2-procedural-review.md
│   └── ...
├── monthly/
│   ├── 2026-01-C1-public-content.md
│   ├── 2026-01-C2-strategic-plan.md
│   └── ...
├── quarterly/
│   └── 2026-Q1-C3-health-scorecard.md
└── annual/
    └── 2026-C4-annual-review.md
```

---

## Implementation Workflow

### Daily Routine (15-30 minutes)

| Time | Action |
|------|--------|
| Morning | Run A1 (meetings) and A2 (permits) |
| Review | Flag urgent items requiring immediate attention |
| Alert | Notify team if critical hearing/deadline detected |

### Weekly Routine (3-4 hours total)

| Day | Action |
|-----|--------|
| Monday | Run A3 (legislative) and A4 (relationships) |
| Wednesday | Compile week's scout data, note patterns |
| Friday | Run B1 (impact) and B2 (procedural) |
| Friday PM | Review analysis, identify priorities, brief coalition |

### Monthly Routine (4-6 hours)

| Week | Action |
|------|--------|
| Week 4 | Run C1 (content generator) and C2 (campaign planner) |
| Week 4 | Compile monthly report package |
| Week 1 (new month) | Publish newsletter, launch social content, brief volunteers |
| Week 1 | Conduct retrospective on previous month's effectiveness |

### Quarterly Routine (2-3 hours)

- Run C3 (Democratic Health Scorecard)
- Assess cumulative trends across all domains
- Adjust strategy based on scorecard findings
- Share key metrics with coalition and public

### Annual Routine (4-6 hours)

- Run C4 (Annual Review & Forecast)
- Full synthesis of year's findings
- Identify multi-year patterns
- Develop strategic priorities for coming year
- Publish annual report to community

---

## Output Pipeline

```
┌─────────────┐     ┌─────────────┐     ┌─────────────────┐
│   SCOUTS    │────▶│  ANALYSTS   │───▶│  SYNTHESIZERS  │
│  (Raw Data) │     │ (Insights)  │     │ (Public Content)│
└─────────────┘     └─────────────┘     └────────┬────────┘
                                                 │
                                                 ▼
                                    ┌────────────────────────┐
                                    │    KNOWLEDGE BASE      │
                                    │  (Searchable Archive)  │
                                    └────────────┬───────────┘
                                                 │
                    ┌────────────────────────────┼────────────────────────────┐
                    ▼                            ▼                            ▼
           ┌───────────────┐           ┌─────────────────┐           ┌───────────────┐
           │  Newsletter   │           │  Social Media   │           │ Blog/Substack │
           │   (Weekly)    │           │ (Daily/Weekly)  │           │  (In-depth)   │
           └───────────────┘           └─────────────────┘           └───────────────┘
                    │                            │                            │
                    └────────────────────────────┼────────────────────────────┘
                                                 ▼
                                    ┌────────────────────────┐
                                    │   INFORMED CITIZENS    │
                                    │  (Taking Action)       │
                                    └────────────────────────┘
```

---

## Key Data Sources

### City of Alachua
- City Commission agendas and minutes
- Planning & Zoning Board materials
- City ordinances and comprehensive plan
- Permit applications and staff reports
- Public records portal

### Alachua County
- Board of County Commissioners agendas/minutes
- Environmental Protection Department
- Growth Management Department
- County code and comprehensive plan
- Development review applications

### State of Florida
- Department of Environmental Protection (DEP)
- Water Management Districts (SRWMD, SJRWMD)
- Florida Legislature bill tracking
- Administrative hearing records (DOAH)
- Sunbiz corporate registry

### Federal
- EPA Region 4 actions
- Army Corps of Engineers permits
- USGS water monitoring data

### Other
- Local news (Gainesville Sun, Alachua County Today)
- Campaign finance records
- Property appraiser records
- Court records (when relevant)

*Full URLs and access details maintained in `config/source-registry.md`*

---

## Primary Use Case: Mill Creek Sink & Tara Development

This system was developed in response to the proposed Tara development—a 1,000+ home project on ~580 acres of karst terrain directly connected to Mill Creek Sink and the Floridan Aquifer.

### Why This Matters

- Water entering Mill Creek Sink reaches Hornsby Spring in **12 days**
- Contamination risks are immediate, not theoretical
- Procedural irregularities and potential conflicts of interest have been documented
- Whistleblower allegations from resigned city planner raise serious accountability questions

### What This System Enables

**Immediate:** Monitor all Tara-related hearings, permits, and regulatory actions

**Ongoing:** Track cumulative development impacts on karst terrain and aquifer recharge areas

**Systemic:** Document patterns of procedural shortcuts, conflicts of interest, and accountability gaps

**Long-term:** Build evidence base for stronger karst protection ordinances and democratic reforms

---

## Core Principles

### 1. Evidence-Based Analysis
All claims traceable to documented sources. Acknowledge uncertainty. Never overstate conclusions.

### 2. Earth as Compass
Frame issues around shared values—clean water, public safety, environmental stewardship—not partisan divisions. Left/right framing divides; water unites.

### 3. Accessibility
Transform technical, legal, and regulatory language into plain language any community member can understand and act upon.

### 4. Actionability
Every report answers: *"What can a concerned citizen do with this information?"* Include specific actions, deadlines, and participation opportunities.

### 5. Transparency About Process
Be clear about what AI analysis can and cannot do. Augments human judgment—does not replace community engagement.

### 6. Respect for Democratic Processes
The goal is to make democracy work better, not to circumvent it. Strengthen public participation, don't undermine legitimate institutions.

---

## Best Practices

### Consistency is Key
- Set a regular schedule and maintain it
- Daily scouts catch things weekly scouts miss
- Cumulative data reveals patterns individual snapshots don't

### Verify Before Acting
- Always check AI outputs against primary sources
- Cite documents, not AI summaries
- When in doubt, file a public records request

### Build Institutional Knowledge
- Save all outputs in organized folders
- Tag for easy retrieval
- Build entity profiles over time (developers, officials, consultants)

### Share Intelligently
- Raw intelligence reports → internal only
- Public content (from C1) → share widely
- Procedural violations → may need legal review first

### Protect Privacy
- Track only public figures acting in public capacity
- No doxxing of private citizens
- Focus on decisions and processes, not personal attacks

### Iterate and Improve
- Note what works and what doesn't
- Adjust prompts based on results
- Share improvements with the community

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| AI can't access websites | Manually copy/paste agendas and documents into prompt, then ask AI to analyze |
| Too much data, AI overwhelmed | Break into smaller chunks (one meeting, one permit at a time) |
| Outputs too long/verbose | Add to prompt: "Be concise. Prioritize top 3 items. Use bullets." |
| Outputs too technical | Use C1 (Content Generator) to translate into plain language |
| Not finding key information | Check source registry—website may have changed. Update URLs. |
| Outputs not actionable | Emphasize in prompt: "Focus on next steps with specific deadlines." |

---

## Customization for Other Communities

This system can be adapted for any community:

### 1. Update Data Sources
Replace Alachua URLs with your jurisdiction's websites in `config/source-registry.md`

### 2. Customize Keywords
- Replace "Mill Creek Sink" with your local environmental features
- Update "Tara April" with your current development threat
- Adjust priorities (karst → coastal → wetlands, etc.)

### 3. Adjust Legal Framework
- Verify state/local procedural requirements
- Update Sunshine Law citations if different state
- Add local charter requirements

### 4. Tailor Messaging
- Reflect your community's values and culture
- Adjust tone for local political climate

---

## Technical Requirements

### AI System
- Works with any AI accepting long-form prompts
- **Recommended:** Claude Sonnet or Opus for best results
- Can use API or chat interface

### Skills Needed
- Basic markdown editing
- Web research (following links, reading documents)
- Copy/paste and file organization
- No coding required

### Time Commitment
| Level | Hours/Week |
|-------|------------|
| Minimum | 2-3 hrs (daily scouts only) |
| Recommended | 5-8 hrs (scouts + analysis) |
| Full System | 10-15 hrs (includes synthesis and campaigns) |

---

## Legal & Ethical Notes

### This System is Legal
- Uses only publicly available information
- Exercises First Amendment rights to monitor government
- Public records requests are a protected legal right

### Use Responsibly
- Stick to facts, cite sources
- Distinguish facts from opinions/interpretations
- Avoid defamation (don't make false claims)
- Recognize that people can have multiple roles without impropriety
- Goal is transparency and accountability, not personal attacks

### When in Doubt
- Consult an attorney before publishing allegations of wrongdoing
- Have experts review technical claims
- Use "according to documents" language

---

## Acknowledgments

This system stands on the shoulders of those who came before:

**Marian Havlik** — "The Clam Lady," who successfully challenged the U.S. Army Corps of Engineers over endangered species protection. Her values of courage, long-term commitment, and willingness to challenge powerful institutions inspire this work.

**Our Alachua Water** — Coalition partners in water protection whose collaboration strengthens this effort.

**Justin Tabor** — Resigned city planner whose whistleblowing exposed the need for systematic monitoring of government accountability.

**All citizen advocates** — Who show up to meetings, submit comments, file records requests, and hold power accountable. This system exists to multiply your effectiveness.

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | January 2026 | Initial release: 10 core prompts, configured for Alachua FL, karst/aquifer protection focus |

---

## Contact

**Project Lead:** Hans  
**Coalition:** Our Alachua Water  
**Publication:** [Substack]

---

*"The health of our democracy depends on informed, engaged citizens. These tools exist to lower the barriers to civic participation and ensure that public decisions serve public interests."*

**Let's protect our water, our community, and our democracy. 💧🌍✊**