---
name: vue-saas-redesign
description: Redesign a Vue 3 application's UI into a modern SaaS-style interface — vertical navigation sidebar replacing a top nav bar, a single spacing scale, and consistent card/table/form treatments. Use when asked to modernize, restyle, or polish the app shell, move navigation into a sidebar, or make the UI look professional and consistent.
---

# Vue 3 → SaaS-Style UI Redesign

Converts a Vue 3 app with a horizontal top nav into a modern SaaS layout: a fixed
vertical sidebar on the left, a scrolling content column on the right, and one
spacing/type/color scale applied everywhere.

This is a **restyle, not a rewrite.** Routes, composables, API calls, and computed
properties must come out the other side unchanged. If a step requires editing
business logic, you have gone out of scope — stop and flag it instead.

## When to use

- "Make this look like a modern SaaS app"
- "Move the nav into a sidebar"
- "The spacing is inconsistent / it looks unpolished"
- "Redesign the UI" on a Vue 3 codebase

## Delegation

Per the project's CLAUDE.md, **any create-or-significantly-modify on a `.vue` file
goes to the `vue-expert` subagent.** This redesign touches many `.vue` files, so
plan the token work here, then hand each file's edit to `vue-expert` with the token
table and the target markup inlined in the prompt. Verify the result in a browser
with the Playwright MCP tools; do not accept "done" without a screenshot.

---

## Step 0 — Audit before editing (do not skip)

A sidebar migration breaks things that a grep for "nav" will not find. Inventory
these four first and write the list down:

1. **Global vs scoped styles.** Find which file holds the app-wide classes
   (`.card`, `.stat-card`, `.badge`, `.page-header`, `table`). In this project
   that is the *unscoped* `<style>` block in `client/src/App.vue`. Redefining
   those inside a view's `<style scoped>` produces two competing definitions —
   always change the global one.

2. **Hardcoded nav-height offsets.** Any `position: sticky` element below the
   header has a `top` value equal to the header's height. Grep for it:

   ```bash
   grep -rn "position: sticky\|position: fixed" client/src/
   grep -rn "70px" client/src/   # whatever the current header height is
   ```

   In this project `App.vue` sets `.nav-container { height: 70px }` and
   `FilterBar.vue` independently hardcodes `top: 70px`. **These two numbers are
   coupled with nothing enforcing it.** In a sidebar layout the filter bar's
   sticky offset becomes `0` (or the height of whatever slim topbar you keep).
   Replace both with a shared CSS custom property so they cannot drift again.

3. **Modal z-index and overlays.** Every `position: fixed` modal must still sit
   above the new sidebar. Note the sidebar's `z-index` and keep modals above it.

4. **Max-width containers.** A centered `max-width` wrapper (here
   `.nav-container` and `.main-content`, both `1600px`) must move *inside* the
   content column, or the page will center itself against the viewport and look
   visibly off-axis next to the sidebar.

---

## Step 1 — Define tokens once

Put these on `:root` in the **global** style block. Every subsequent value in the
redesign references a token; no new raw hex or pixel values anywhere.

```css
:root {
  /* Spacing — a 4px base scale. Use ONLY these. */
  --space-1: 0.25rem;  --space-2: 0.5rem;   --space-3: 0.75rem;
  --space-4: 1rem;     --space-5: 1.5rem;   --space-6: 2rem;
  --space-7: 3rem;

  /* Surfaces & lines */
  --bg-app: #f8fafc;        /* page behind the cards */
  --bg-surface: #ffffff;    /* cards, tables, sidebar */
  --bg-sunk: #f1f5f9;       /* table headers, hover rows */
  --border: #e2e8f0;
  --border-strong: #cbd5e1;

  /* Text */
  --text: #0f172a;
  --text-soft: #475569;
  --text-faint: #64748b;
  --text-inverse: #ffffff;

  /* Accent & status */
  --accent: #2563eb;
  --accent-soft: #eff6ff;
  --green: #16a34a;  --blue: #2563eb;
  --amber: #ca8a04;  --red: #dc2626;

  /* Shape */
  --radius: 8px;
  --radius-lg: 12px;
  --shadow-sm: 0 1px 2px rgba(15, 23, 42, 0.04);
  --shadow: 0 1px 3px rgba(15, 23, 42, 0.08), 0 1px 2px rgba(15, 23, 42, 0.04);

  /* Layout */
  --sidebar-w: 248px;
  --sidebar-w-collapsed: 68px;
  --topbar-h: 0px;   /* set to the slim topbar's height if you keep one */
}
```

Keep the project's existing palette family (this app is slate/gray with
green/blue/amber/red status colors, no emoji in UI). A redesign changes
*structure and rhythm*, not brand identity — do not introduce a new hue.

---

## Step 2 — The app shell

Replace the stacked `header / filters / main` flow with a two-column grid. The
sidebar is fixed-height and does not scroll with content; the content column owns
all vertical scrolling.

```vue
<!-- App.vue template -->
<template>
  <div class="app-shell">
    <AppSidebar :collapsed="sidebarCollapsed" @toggle="sidebarCollapsed = !sidebarCollapsed" />

    <div class="app-main">
      <FilterBar />
      <main class="app-content">
        <router-view />
      </main>
    </div>

    <!-- Modals stay at shell level so they overlay the sidebar too -->
    <ProfileDetailsModal :is-open="showProfileDetails" @close="showProfileDetails = false" />
    <TasksModal :is-open="showTasks" :tasks="tasks" @close="showTasks = false" />
  </div>
</template>
```

```css
.app-shell {
  display: grid;
  grid-template-columns: var(--sidebar-w) 1fr;
  min-height: 100vh;
  background: var(--bg-app);
  transition: grid-template-columns 0.2s ease;
}

.app-shell.is-collapsed { grid-template-columns: var(--sidebar-w-collapsed) 1fr; }

.app-main {
  display: flex;
  flex-direction: column;
  min-width: 0;            /* REQUIRED: lets wide tables shrink instead of
                              stretching the grid column past the viewport */
}

.app-content {
  flex: 1;
  width: 100%;
  max-width: 1400px;       /* the centering wrapper now lives INSIDE the column */
  margin: 0 auto;
  padding: var(--space-6);
}
```

`min-width: 0` on the content column is the single most common cause of a
sidebar layout "leaking" horizontal scroll onto `body`. Set it every time.

---

## Step 3 — The sidebar component

Create `client/src/components/AppSidebar.vue`. Structure: brand → nav links →
spacer → utilities (language, profile) pinned to the bottom.

```vue
<template>
  <aside class="sidebar" :class="{ collapsed }">
    <div class="sidebar-brand">
      <span class="brand-mark">CC</span>
      <span v-show="!collapsed" class="brand-text">
        <span class="brand-name">{{ t('nav.companyName') }}</span>
        <span class="brand-sub">{{ t('nav.subtitle') }}</span>
      </span>
    </div>

    <nav class="sidebar-nav">
      <router-link
        v-for="item in navItems"
        :key="item.to"
        :to="item.to"
        class="nav-item"
        :title="collapsed ? t(item.label) : null"
      >
        <span class="nav-icon" v-html="item.icon"></span>
        <span v-show="!collapsed" class="nav-label">{{ t(item.label) }}</span>
      </router-link>
    </nav>

    <div class="sidebar-footer">
      <LanguageSwitcher :compact="collapsed" />
      <ProfileMenu :compact="collapsed" @show-profile-details="$emit('show-profile-details')" />
      <button class="collapse-btn" @click="$emit('toggle')" :aria-label="collapsed ? 'Expand' : 'Collapse'">
        <!-- chevron -->
      </button>
    </div>
  </aside>
</template>
```

Drive the links from **data, not markup** — one array replaces seven near-identical
`<router-link>` blocks and is where a new tab gets added:

```javascript
const navItems = [
  { to: '/',            label: 'nav.overview',       icon: ICONS.grid },
  { to: '/inventory',   label: 'nav.inventory',      icon: ICONS.box },
  { to: '/orders',      label: 'nav.orders',         icon: ICONS.receipt },
  { to: '/spending',    label: 'nav.finance',        icon: ICONS.wallet },
  { to: '/demand',      label: 'nav.demandForecast', icon: ICONS.trend },
  { to: '/reports',     label: 'nav.reports',        icon: ICONS.chart },
  { to: '/restocking',  label: 'nav.restocking',     icon: ICONS.refresh },
]
```

Two things to get right:

- **Every label goes through `t()`.** Hardcoded English in the nav is the most
  common regression in this repo — `App.vue` currently has a literal `Reports`
  string sitting among six translated siblings. Add the missing keys to *both*
  `locales/en.js` and `locales/ja.js`. Note that this project's `t()` returns the
  **key itself** when a translation is missing, so `t('x') || 'fallback'` is dead
  code that renders `x` — there is no truthy-fallback idiom available.
- **Use `router-link`'s own active class.** Drop the
  `:class="{ active: $route.path === '/x' }"` pattern; vue-router applies
  `router-link-active` / `router-link-exact-active` for free. Style
  `.nav-item.router-link-exact-active` and delete the manual comparison.

Sidebar styling:

```css
.sidebar {
  position: sticky;
  top: 0;
  height: 100vh;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-4) var(--space-3);
  background: var(--bg-surface);
  border-right: 1px solid var(--border);
  z-index: 50;              /* below modals, above content */
}

.sidebar-nav { display: flex; flex-direction: column; gap: 2px; }

.nav-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius);
  color: var(--text-faint);
  font-size: 0.9rem;
  font-weight: 500;
  text-decoration: none;
  white-space: nowrap;
  transition: background 0.15s ease, color 0.15s ease;
}

.nav-item:hover { background: var(--bg-sunk); color: var(--text); }

.nav-item.router-link-exact-active {
  background: var(--accent-soft);
  color: var(--accent);
  font-weight: 600;
}

.nav-icon { flex-shrink: 0; width: 18px; height: 18px; display: grid; place-items: center; }

/* Push utilities to the bottom of the column */
.sidebar-footer { margin-top: auto; display: flex; flex-direction: column; gap: var(--space-2); }
```

---

## Step 4 — Normalize spacing

This is what actually makes it read as "polished." Sweep every view and replace
ad-hoc values with tokens. The rules:

| Context | Value |
|---|---|
| Page padding | `--space-6` |
| Gap between cards / sections | `--space-5` |
| Card interior padding | `--space-5` |
| Card header → body | `--space-4` |
| Table cell padding | `--space-3` `--space-4` |
| Label → control | `--space-2` |
| Inline icon → text | `--space-2` |
| Grid gap (stat tiles) | `--space-4` |

One vertical rhythm per page: `page-header` → `--space-5` → first card, and every
card separated by `--space-5`. Delete per-view `margin-bottom` overrides that
fight this; a single `.card { margin-bottom: var(--space-5) }` in the global block
handles all of them.

---

## Step 5 — Component polish

Update the **global** definitions so every view inherits the change at once.

```css
.card {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  margin-bottom: var(--space-5);
  overflow: hidden;              /* lets the header's border reach the edges */
}

.card-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--space-4);
  padding: var(--space-4) var(--space-5);
  border-bottom: 1px solid var(--border);
}

.card-title { font-size: 0.95rem; font-weight: 600; color: var(--text); }

/* Stat tiles: label above, number below, quiet border, no heavy shadow */
.stat-card {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: var(--space-5);
}
.stat-label {
  font-size: 0.75rem; font-weight: 600; letter-spacing: 0.06em;
  text-transform: uppercase; color: var(--text-faint);
  margin-bottom: var(--space-2);
}
.stat-value {
  font-size: 1.75rem; font-weight: 600; color: var(--text);
  font-variant-numeric: tabular-nums;    /* stops digits jittering on update */
}

/* Tables */
thead th {
  background: var(--bg-sunk);
  padding: var(--space-3) var(--space-4);
  font-size: 0.7rem; font-weight: 600; letter-spacing: 0.06em;
  text-transform: uppercase; color: var(--text-faint);
  text-align: left; white-space: nowrap;
}
tbody td {
  padding: var(--space-3) var(--space-4);
  border-bottom: 1px solid var(--border);
  font-size: 0.875rem;
}
tbody tr:last-child td { border-bottom: 0; }
tbody tr:hover { background: var(--bg-sunk); }
.table-container { overflow-x: auto; }   /* wide tables scroll THEMSELVES */
```

`font-variant-numeric: tabular-nums` on every number that updates reactively —
currency, counts, percentages. Without it, filtered totals visibly shift width as
digits change, which is the clearest tell of an unpolished dashboard.

Right-align numeric columns, left-align text columns. Never center a number
column.

---

## Step 6 — Responsive

The sidebar is the only layout element that needs breakpoint work.

```css
/* Tablet: icons only, labels hidden */
@media (max-width: 1024px) {
  .app-shell { grid-template-columns: var(--sidebar-w-collapsed) 1fr; }
  .nav-label, .brand-text { display: none; }
}

/* Mobile: sidebar becomes an off-canvas drawer */
@media (max-width: 768px) {
  .app-shell { grid-template-columns: 1fr; }
  .sidebar {
    position: fixed; inset: 0 auto 0 0;
    width: var(--sidebar-w);
    transform: translateX(-100%);
    transition: transform 0.2s ease;
  }
  .sidebar.open { transform: translateX(0); }
  .app-content { padding: var(--space-4); }
}
```

At the mobile breakpoint add a hamburger to the content column — otherwise the
drawer has no trigger and navigation is unreachable.

---

## Step 7 — Verify

Redesigns regress silently, so check all of it:

```bash
cd client && npx vite build     # catches template/SFC errors the dev server tolerates
```

Then with the Playwright MCP tools, on **every** route:

- [ ] `document.body.scrollWidth <= window.innerWidth` — no horizontal page scroll
- [ ] Sidebar active state matches the current route
- [ ] Filter bar sticks at the right offset (the old `top: 70px` is gone)
- [ ] A modal opens *above* the sidebar, not behind it
- [ ] Wide tables scroll inside `.table-container`, not the page
- [ ] Switch locale to `ja` — no raw translation keys visible, no clipped labels
- [ ] Collapse the sidebar, then reload — layout still correct
- [ ] 1440px, 1024px, and 768px widths all usable
- [ ] Console has no *new* errors (this app has pre-existing `/api/tasks` 404s —
      compare against a baseline rather than assuming a clean console)

---

## Pitfalls

| Symptom | Cause |
|---|---|
| Page scrolls horizontally | Missing `min-width: 0` on the content grid column |
| Content looks off-centre | `max-width` wrapper left outside the content column |
| Filter bar floats or overlaps | Stale `top: 70px` tied to the deleted top nav |
| Modal appears behind sidebar | Modal `z-index` below the sidebar's |
| Styles apply on one view only | Edited a `<style scoped>` block instead of the global one |
| Nav item never highlights | Manual `$route.path` check kept after markup changed |
| Raw keys like `nav.restocking` render | Key added to `en.js` but not `ja.js` |
| Numbers jitter while filtering | Missing `font-variant-numeric: tabular-nums` |
| Sidebar scrolls away | `height: 100vh` / `position: sticky; top: 0` not set |

## Scope boundary

Do **not**, as part of a redesign: rename routes, change API calls, alter
computed-property math, "fix" unrelated bugs found along the way, or add a UI
library. Note them and report them separately — a restyle that also changes
behavior is untestable, because there is no longer a known-good baseline to
compare against.
