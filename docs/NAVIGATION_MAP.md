# Screen & Navigation Map

## Public web
- `index.html` — Home, Features, About (sticky nav + smooth scroll)
- `login.html` — Admin/Reviewer authentication
- `forgot-password.html` — 3-step demo recovery

## Admin (after login → `app.html`)
| Route ID | Purpose |
|----------|---------|
| dashboard | Counts, document status, activity |
| faculty | Search, create/edit, activate/deactivate |
| reviewers | List, assignment modal |
| evalSettings | Tabs: **Scoring Rules** (KRA hierarchy, draft/publish) and **Evaluation Period** (dates, reviewer availability) |
| config / simulationCfg | Legacy route IDs → redirect to `evalSettings` (rules / period tab) |
| reports | Per-faculty KRA breakdown, print |
| activity | Audit-style list |
| profile | Session, reset demo data |

## Reviewer
| Route ID | Purpose |
|----------|---------|
| dashboard | Assigned workload summary, read-only Evaluation Period card |
| assigned | Faculty cards → workspace |
| workspace | KRA → Criterion → Indicator → documents (SET/SEF) |
| review | Document review panel (OCR + actions) |
| evalSettings | Tabs: read-only **Scoring Rules** (published) and **Evaluation Period** |
| rules | Legacy → `evalSettings` (Scoring Rules tab) |
| notifications | Demo alerts for assigned faculty |
| profile | Same as admin profile |

## Flutter faculty
| Screen | Access |
|--------|--------|
| Splash | Auto → Sign in |
| Sign in / Forgot password | Demo auth |
| Shell (bottom nav) | Home · Documents · Simulation · Notifications · Profile |
| My Assessment | Home card → full assessment tree (KRA / SET/SEF / indicators) |
| Rank simulator | Simulation tab + Home “Simulation Result” card (shared engine) |
| Evaluation Period | Home overview row → View Schedule details |
| Assessment drill-down | KRA → Criterion → Indicator → entries |
| SET/SEF | KRA I Criterion A dedicated tabs |
| Upload evidence | Documents → flow |
| Document detail | Status, simulated OCR, feedback |
