# 📚 Open Sousveillance Studio - Source Directory

**A living reference of all government transparency portals and civic data sources.**

> 🔄 **Last Updated:** January 2026  
> 📍 **Primary Focus:** Alachua County, Florida  
> 🌐 **Scope:** Municipal → County → State → Federal

This document serves as a quick-reference guide to all monitored data sources. For technical scraping configurations, see [`config/sources.yaml`](../config/sources.yaml).

---

## 📋 Table of Contents

- [Tier 1: Municipal (City Level)](#tier-1-municipal-city-level)
- [Tier 2: County Level](#tier-2-county-level)
- [Tier 3: Regional (Water Management)](#tier-3-regional-water-management)
- [Tier 4: Legal Notices & Public Records](#tier-4-legal-notices--public-records)
- [Tier 5: News & Civic Organizations](#tier-5-news--civic-organizations)
- [Tier 6: Florida State Government](#tier-6-florida-state-government)
- [Tier 7: US Federal Government](#tier-7-us-federal-government)
- [Specialty Sources](#specialty-sources)
- [Adding New Sources](#adding-new-sources)

---

## 🏘️ Tier 1: Municipal (City Level)

City councils, planning boards, and local permit offices. **Most granular and immediately actionable.**

| Source | What It Contains | URL | Platform | Priority |
|:-------|:-----------------|:----|:---------|:---------|
| **City of Alachua - CivicClerk** | Commission & board agendas, minutes, video | https://alachuafl.portal.civicclerk.com/ | CivicClerk (SPA) | 🔴 Critical |
| **City of Alachua - Calendar** | Upcoming meetings and events | https://www.cityofalachua.com/government/global-pages/calendar-month-view | Granicus | 🟡 High |
| **City of Alachua - Development Map** | Active/proposed development projects | https://www.cityofalachua.com/government/planning-community-development/planning-zoning/land-use-map | ArcGIS | 🔴 Critical |
| **City of High Springs** | City council meetings | https://www.highsprings.us/ | TBD | 🟡 High |
| **City of Gainesville - Legistar** | City commission, CRA, boards | https://gainesville.legistar.com/ | Legistar | 🟢 Medium |

### Key Meeting Bodies (City of Alachua)
- **City Commission** - Primary legislative body
- **Planning & Zoning Board** - Development review
- **Community Redevelopment Agency (CRA)** - Downtown/economic development
- **Code Enforcement Board** - Violations and appeals

---

## 🏛️ Tier 2: County Level

County commission, advisory boards, and county-wide services.

| Source | What It Contains | URL | Platform | Priority |
|:-------|:-----------------|:----|:---------|:---------|
| **Alachua County - eScribe** | BOCC, DRC, EPAC, Planning Commission | https://pub-alachuacounty.escribemeetings.com/ | eScribe | 🔴 Critical |
| **Map Genius (County GIS)** | Development project tracker, parcel data | https://mapgenius.alachuacounty.us/development-projects/ | Custom | 🔴 Critical |
| **Environmental Protection Dept** | Environmental regulations, monitoring | https://alachuacounty.us/Depts/epd/Pages/EPD.aspx | SharePoint | 🟡 High |
| **Growth Management** | Comprehensive plan, land use | https://growth-management.alachuacounty.us/ | Custom | 🟡 High |

### Key Meeting Bodies (Alachua County)
- **Board of County Commissioners (BOCC)** - Primary legislative body
- **Development Review Committee (DRC)** - Pre-application and technical review
- **Environmental Protection Advisory Committee (EPAC)** - Environmental policy
- **Planning Commission** - Comp plan amendments, rezonings

---

## 🌊 Tier 3: Regional (Water Management)

Water Management Districts and regional environmental agencies.

| Source | What It Contains | URL | Platform | Priority |
|:-------|:-----------------|:----|:---------|:---------|
| **SRWMD - Permits** | ERP, Water Use Permits, pre-application | https://www.mysuwanneeriver.com/8/Permits-Rules | CivicPlus | 🔴 Critical |
| **SRWMD - E-Permitting** | Active permit applications | https://permitting.sjrwmd.com/srep/#/ep | Custom | 🔴 Critical |
| **Florida DEP - Oculus** | State environmental permits | https://floridadep.gov/water/submerged-lands-environmental-resources-coordination/content/finding-erp-permit-dep-internet | Custom | 🟡 High |
| **FDOT District 2** | State road projects, access permits | https://nflroads.com/ProjectList.aspx?r=6713 | Custom | 🟢 Medium |

### SRWMD Key Programs
- **Environmental Resource Permits (ERP)** - Stormwater, wetland impacts
- **Water Use Permits (WUP)** - Groundwater withdrawal
- **Pre-Application Meetings** - Earliest signal of new projects!

---

## ⚖️ Tier 4: Legal Notices & Public Records

Official legal notices, court filings, and corporate records.

| Source | What It Contains | URL | Platform | Priority |
|:-------|:-----------------|:----|:---------|:---------|
| **Florida Public Notices** | Statewide legal notice repository | https://floridapublicnotices.com/ | Custom | 🔴 Critical |
| **Mainstreet Daily News** | Local certified publisher | https://www.mainstreetdailynews.com/public-notices | WordPress | 🔴 Critical |
| **Florida Sunbiz** | Corporate registrations, annual reports | https://search.sunbiz.org/Inquiry/CorporationSearch/ByName | Custom | 🟡 High |
| **Alachua County Clerk** | Court records, property, liens | https://www.alachuaclerk.org/court_records/index.cfm | Custom | 🟡 High |
| **Property Appraiser** | Ownership, valuations, exemptions | https://www.acpafl.org/ | Custom | 🟡 High |

### Notice Types to Watch
- **Public Hearings** - Zoning changes, comp plan amendments
- **Bid Notices** - Government contracts
- **Foreclosure/Tax Sales** - Property ownership changes
- **Name Changes (LLCs)** - Developer entity restructuring

---

## 📰 Tier 5: News & Civic Organizations

Media and advocacy groups that provide analysis and break stories.

| Source | What It Contains | URL | Platform | Priority |
|:-------|:-----------------|:----|:---------|:---------|
| **WUFT Environment** | Public media - environmental coverage | https://www.wuft.org/environment | WordPress (RSS) | 🟡 High |
| **Our Santa Fe River** | Springs advocacy, technical reports | https://oursantaferiver.org/ | WordPress | 🟡 High |
| **Gainesville Sun** | Regional newspaper | https://www.gainesville.com/ | Gannett | 🟢 Medium |
| **Florida Springs Council** | Statewide springs policy | https://floridaspringscouncil.org/ | WordPress | 🟢 Medium |

---

## 🏛️ Tier 6: Florida State Government

Statewide agencies, legislature, and administrative bodies.

### Legislature & Rulemaking

| Source | What It Contains | URL | API? | Priority |
|:-------|:-----------------|:----|:-----|:---------|
| **Florida House** | Bills, committees, votes | https://www.myfloridahouse.gov/ | No | 🟡 High |
| **Florida Senate** | Bills, committees | https://www.flsenate.gov/ | No | 🟡 High |
| **FL Administrative Register** | Proposed rules, agency notices | https://www.flrules.org/ | No | 🔴 Critical |
| **Governor & Cabinet** | Cabinet meeting agendas | https://www.flgov.com/cabinet-meetings/ | No | 🟢 Medium |

### Environmental Agencies

| Source | What It Contains | URL | API? | Priority |
|:-------|:-----------------|:----|:-----|:---------|
| **FL DEP Public Notices** | Permits, enforcement, consent orders | https://floridadep.gov/ogc/ogc/content/public-notices | No | 🔴 Critical |
| **FL Geological Survey** | Karst maps, sinkhole reports | https://floridadep.gov/fgs | No | 🟡 High |
| **Division of Elections** | Campaign finance, initiatives | https://dos.myflorida.com/elections/ | No | 🟢 Medium |

### Bill Tracking Keywords
- `springs`, `aquifer`, `water management`
- `comprehensive plan`, `development of regional impact`
- `home rule`, `local government preemption`

---

## 🇺🇸 Tier 7: US Federal Government

Federal agencies with oversight of environmental and water issues.

### Regulatory & Rulemaking

| Source | What It Contains | URL | API? | Priority |
|:-------|:-----------------|:----|:-----|:---------|
| **Federal Register** | Rules, proposed rules, notices | https://www.federalregister.gov/ | ✅ REST | 🟡 High |
| **Regulations.gov** | Public comment on rules | https://www.regulations.gov/ | ✅ REST | 🟡 High |
| **Congress.gov** | Bills, hearings, votes | https://www.congress.gov/ | ✅ REST | 🟢 Medium |
| **GovInfo** | CFR, Congressional Record | https://www.govinfo.gov/ | ✅ REST | 🟢 Medium |

### Environmental Oversight

| Source | What It Contains | URL | API? | Priority |
|:-------|:-----------------|:----|:-----|:---------|
| **EPA ECHO** | Compliance, violations, enforcement | https://echo.epa.gov/ | ✅ REST | 🔴 Critical |
| **USGS Water Resources** | Real-time well levels, aquifer data | https://waterdata.usgs.gov/nwis | ✅ REST | 🟡 High |
| **Army Corps (Jacksonville)** | Section 404 wetland permits | https://www.saj.usace.army.mil/Missions/Regulatory/Public-Notices/ | No | 🔴 Critical |
| **USASpending** | Federal grants and contracts | https://www.usaspending.gov/ | ✅ REST | 🟢 Medium |
| **FOIA.gov** | FOIA request portal | https://www.foia.gov/ | No | 🟢 Low |

### Federal API Keys Needed
- **api.data.gov** - Regulations.gov, GovInfo (free, instant)
- **api.congress.gov** - Congress.gov (free, instant)
- No key needed for Federal Register, USGS, EPA ECHO

---

## 🔬 Specialty Sources

### Karst & Hydrogeology
| Source | Description | URL |
|:-------|:------------|:----|
| Florida Geological Survey | Sinkhole reports, karst maps | https://floridadep.gov/fgs |
| USGS Floridan Aquifer | Scientific publications | https://www.usgs.gov/mission-areas/water-resources |
| UF Water Institute | Academic research | https://waterinstitute.ufl.edu/ |

### Development & Real Estate
| Source | Description | URL |
|:-------|:------------|:----|
| Sunbiz LLC Search | Corporate registrations | https://search.sunbiz.org/ |
| Property Appraiser | Ownership, valuations | https://www.acpafl.org/ |
| Zillow/Redfin | Market activity signals | N/A (reference only) |

### Coalition Partners
| Organization | Focus | URL |
|:-------------|:------|:----|
| Our Alachua Water | Mill Creek Sink protection | https://ouralachuawater.org/ |
| Our Santa Fe River | Springs protection | https://oursantaferiver.org/ |
| Sierra Club Florida | Environmental litigation | https://www.sierraclub.org/florida |

---

## ➕ Adding New Sources

To add a new source:

1. **Add to this document** in the appropriate tier section
2. **Add to `config/sources.yaml`** with full scraping configuration
3. **Test the scraper** to ensure data extraction works
4. **Document any special requirements** (login, API key, etc.)

### Template for New Source

```yaml
- id: "unique-source-id"
  name: "Human Readable Name"
  description: "What this source contains"
  jurisdiction: "City/County/State"
  url: "https://example.gov/"
  platform: "civicclerk|escribe|custom|api"
  priority: "critical|high|medium|low"
  check_frequency: "daily|weekly|monthly"
  scraping:
    method: "playwright|beautifulsoup|api"
    requires_javascript: true|false
  document_types:
    - "agenda"
    - "permit"
  notes: "Any special instructions for maintainers"
```

---

## 📊 Source Statistics

| Tier | Count | Critical | High | Medium | Low |
|:-----|:------|:---------|:-----|:-------|:----|
| 1 - Municipal | 5 | 2 | 2 | 1 | 0 |
| 2 - County | 4 | 2 | 2 | 0 | 0 |
| 3 - Regional | 4 | 1 | 2 | 1 | 0 |
| 4 - Legal | 5 | 2 | 3 | 0 | 0 |
| 5 - Civic | 4 | 0 | 2 | 2 | 0 |
| 6 - State | 8 | 2 | 4 | 2 | 0 |
| 7 - Federal | 9 | 2 | 3 | 3 | 1 |
| **TOTAL** | **39** | **11** | **18** | **9** | **1** |

---

## 🔗 Quick Links by Use Case

### "I need to find a meeting agenda"
→ [CivicClerk (City)](#tier-1-municipal-city-level) | [eScribe (County)](#tier-2-county-level)

### "I need to check for new development permits"
→ [SRWMD E-Permitting](#tier-3-regional-water-management) | [Army Corps Notices](#tier-7-us-federal-government)

### "I need to research a developer/LLC"
→ [Sunbiz](#tier-4-legal-notices--public-records) | [Property Appraiser](#tier-4-legal-notices--public-records)

### "I need to track a state bill"
→ [FL House](#tier-6-florida-state-government) | [FL Senate](#tier-6-florida-state-government)

### "I need environmental compliance data"
→ [EPA ECHO](#tier-7-us-federal-government) | [FL DEP Notices](#tier-6-florida-state-government)

### "I need to file a public comment"
→ [Regulations.gov (Federal)](#tier-7-us-federal-government) | [FL Admin Register (State)](#tier-6-florida-state-government)

---

**Last Updated:** January 2026  
**Maintained By:** Open Sousveillance Studio Contributors  
**License:** MIT
