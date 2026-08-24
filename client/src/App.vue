<template>
  <div class="app-shell" :class="{ 'is-collapsed': sidebarCollapsed }">
    <AppSidebar
      :collapsed="sidebarCollapsed"
      @toggle="toggleSidebar"
      @show-profile-details="showProfileDetails = true"
      @show-tasks="showTasks = true"
    />

    <div class="app-main">
      <FilterBar />
      <main class="app-content">
        <router-view />
      </main>

      <!-- Operator information area, as a 3270 panel carries at its foot -->
      <div class="status-line">
        <span class="field">SYS <b>CATALYST.INVMGT</b></span>
        <span class="field">TERM <b>3278-2</b></span>
        <span class="field">SCRN <b>{{ screenId }}</b></span>
        <span class="field">USER <b>{{ terminalUser }}</b></span>
        <span class="field ready">READY<span class="cursor">&#9608;</span></span>
      </div>
    </div>

    <!-- Modals live at shell level so they overlay the sidebar, not sit under it -->
    <ProfileDetailsModal
      :is-open="showProfileDetails"
      @close="showProfileDetails = false"
    />

    <TasksModal
      :is-open="showTasks"
      :tasks="tasks"
      @close="showTasks = false"
      @add-task="addTask"
      @delete-task="deleteTask"
      @toggle-task="toggleTask"
    />
  </div>
</template>

<script>
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { api } from './api'
import { useAuth } from './composables/useAuth'
import { useI18n } from './composables/useI18n'
import AppSidebar from './components/AppSidebar.vue'
import FilterBar from './components/FilterBar.vue'
import ProfileDetailsModal from './components/ProfileDetailsModal.vue'
import TasksModal from './components/TasksModal.vue'

export default {
  name: 'App',
  components: {
    AppSidebar,
    FilterBar,
    ProfileDetailsModal,
    TasksModal
  },
  setup() {
    const { currentUser } = useAuth()
    const { t } = useI18n()
    const route = useRoute()

    // 3270 panels are identified by a short screen name, not a URL.
    const SCREEN_IDS = {
      '/': 'OVERVIEW',
      '/inventory': 'INVENTRY',
      '/orders': 'ORDERS',
      '/spending': 'FINANCE',
      '/demand': 'DEMAND',
      '/reports': 'REPORTS',
      '/restocking': 'RESTOCK'
    }
    const screenId = computed(() => SCREEN_IDS[route.path] || 'UNKNOWN')

    // Terminal-style user id: first initial + surname, truncated to 8 chars,
    // which is what a mainframe login would actually be.
    const terminalUser = computed(() => {
      const parts = (currentUser.value.name || '').split(' ').filter(Boolean)
      if (parts.length === 0) return 'GUEST'
      const id = parts.length > 1
        ? parts[0][0] + parts[parts.length - 1]
        : parts[0]
      return id.toUpperCase().slice(0, 8)
    })
    const showProfileDetails = ref(false)
    const showTasks = ref(false)

    // Sidebar collapse survives reloads, matching how useI18n persists locale.
    const sidebarCollapsed = ref(localStorage.getItem('sidebar-collapsed') === 'true')

    const toggleSidebar = () => {
      sidebarCollapsed.value = !sidebarCollapsed.value
      localStorage.setItem('sidebar-collapsed', String(sidebarCollapsed.value))
    }
    const apiTasks = ref([])

    // Merge mock tasks from currentUser with API tasks
    const tasks = computed(() => {
      return [...currentUser.value.tasks, ...apiTasks.value]
    })

    const loadTasks = async () => {
      try {
        apiTasks.value = await api.getTasks()
      } catch (err) {
        console.error('Failed to load tasks:', err)
      }
    }

    const addTask = async (taskData) => {
      try {
        const newTask = await api.createTask(taskData)
        // Add new task to the beginning of the array
        apiTasks.value.unshift(newTask)
      } catch (err) {
        console.error('Failed to add task:', err)
      }
    }

    const deleteTask = async (taskId) => {
      try {
        // Check if it's a mock task (from currentUser)
        const isMockTask = currentUser.value.tasks.some(t => t.id === taskId)

        if (isMockTask) {
          // Remove from mock tasks
          const index = currentUser.value.tasks.findIndex(t => t.id === taskId)
          if (index !== -1) {
            currentUser.value.tasks.splice(index, 1)
          }
        } else {
          // Remove from API tasks
          await api.deleteTask(taskId)
          apiTasks.value = apiTasks.value.filter(t => t.id !== taskId)
        }
      } catch (err) {
        console.error('Failed to delete task:', err)
      }
    }

    const toggleTask = async (taskId) => {
      try {
        // Check if it's a mock task (from currentUser)
        const mockTask = currentUser.value.tasks.find(t => t.id === taskId)

        if (mockTask) {
          // Toggle mock task status
          mockTask.status = mockTask.status === 'pending' ? 'completed' : 'pending'
        } else {
          // Toggle API task
          const updatedTask = await api.toggleTask(taskId)
          const index = apiTasks.value.findIndex(t => t.id === taskId)
          if (index !== -1) {
            apiTasks.value[index] = updatedTask
          }
        }
      } catch (err) {
        console.error('Failed to toggle task:', err)
      }
    }

    onMounted(loadTasks)

    return {
      t,
      sidebarCollapsed,
      toggleSidebar,
      screenId,
      terminalUser,
      showProfileDetails,
      showTasks,
      tasks,
      addTask,
      deleteTask,
      toggleTask
    }
  }
}
</script>

<style>
/* ===========================================================================
   Tokens — IBM 3270 greenscreen terminal.

   Monochrome P1 phosphor on a dark CRT, with the 3270's extended-colour set
   reserved strictly for status. Hierarchy comes from INTENSITY (bright /
   normal / dim green), not from hue — which is how a real terminal did it.
   No radii, no shadows, no gradients: a CRT cannot draw them.
   =========================================================================== */

:root {
  /* Spacing — 4px base scale, unchanged */
  --space-1: 0.25rem;
  --space-2: 0.5rem;
  --space-3: 0.75rem;
  --space-4: 1rem;
  --space-5: 1.5rem;
  --space-6: 2rem;

  /* Type — one fixed-width family for everything */
  --font-ui: 'IBM Plex Mono', ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  --font-mono: var(--font-ui);

  /* Screen. Not pure black — a CRT's unlit phosphor carries a faint cast. */
  --bg-app: #030704;
  --bg-surface: #060d07;
  --bg-sunk: #0b170d;
  --border: #1c5325;
  --border-strong: #2c8038;

  /* Phosphor intensity ladder */
  --text: #33e659;
  --text-soft: #24ab3f;
  --text-faint: #1a8330;
  --text-dim: #135f23;

  /* Terminal chrome (the sidebar reads as the surrounding hardware) */
  --bezel: #020502;
  --bezel-raised: #0b170d;
  --bezel-line: #1c5325;
  --bezel-tick: #2c8038;
  --bezel-text: #24ab3f;
  --bezel-text-dim: #16702a;
  --bezel-text-strong: #7dffa0;

  /* Accent — a single bright-phosphor highlight, the terminal's "high
     intensity" attribute. Replaces the previous copper. */
  --accent: #7dffa0;
  --accent-bright: #c8ffd6;
  --accent-deep: #33e659;
  --accent-dim: rgba(125, 255, 160, 0.16);
  --accent-soft: rgba(125, 255, 160, 0.09);
  --accent-tint: rgba(125, 255, 160, 0.14);
  --accent-border: #3f9c4d;

  /* Status — the 3270 extended-colour palette, used only for meaning */
  --green: #33e659;   --green-soft: rgba(51, 230, 89, 0.12);   --green-deep: #7dffa0;   --green-border: #2c8038;
  --blue: #6fb3ff;    --blue-soft: rgba(111, 179, 255, 0.12);  --blue-deep: #a8d2ff;    --blue-border: #3f6f9c;
  --amber: #e6c23a;   --amber-soft: rgba(230, 194, 58, 0.12);  --amber-deep: #ffe680;   --amber-border: #8f7a24;
  --red: #ff5f56;     --red-soft: rgba(255, 95, 86, 0.12);     --red-deep: #ff9d97;     --red-border: #9c3f3a;

  /* Chart series — phosphor intensities first, then the two status hues that
     stay legible on black. Keeps multi-series charts readable without
     inventing colours the terminal never had. */
  --series-1: #7dffa0;
  --series-2: #24ab3f;
  --series-3: #6fb3ff;
  --series-4: #e6c23a;
  --series-1-soft: rgba(125, 255, 160, 0.12);
  --series-2-soft: rgba(36, 171, 63, 0.12);
  --series-3-soft: rgba(111, 179, 255, 0.12);
  --series-4-soft: rgba(230, 194, 58, 0.12);

  /* Shape — a CRT draws no curves and casts no shadow */
  --radius: 0;
  --radius-lg: 0;
  --shadow-sm: none;
  --shadow-md: none;

  /* Phosphor bloom */
  --glow: 0 0 4px rgba(51, 230, 89, 0.35);
  --glow-bright: 0 0 6px rgba(125, 255, 160, 0.5);

  /* Layout */
  --sidebar-w: 236px;
  --sidebar-w-collapsed: 60px;
  --topbar-h: 0px;
}

/* ---------------------------------------------------------------------------
   Reset & base
   --------------------------------------------------------------------------- */

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
  font-family: var(--font-ui);
  background: var(--bg-app);
  color: var(--text);
  font-size: 0.8125rem;
  line-height: 1.5;
  /* Deliberately NOT antialiased: crisp pixel edges are the point. */
  -webkit-font-smoothing: none;
  font-smooth: never;
  text-shadow: var(--glow);
}

/* ---------------------------------------------------------------------------
   Shell: hardware chrome on the left, screen on the right
   --------------------------------------------------------------------------- */

.app-shell {
  position: relative;
  display: grid;
  grid-template-columns: var(--sidebar-w) 1fr;
  min-height: 100vh;
  transition: grid-template-columns 0.2s ease;
}

.app-shell.is-collapsed { grid-template-columns: var(--sidebar-w-collapsed) 1fr; }

/* CRT scanlines. Fixed and non-interactive so it overlays the whole screen
   without entering the hit-testing path. Kept very low contrast — the effect
   should read as texture, not as stripes over the data. */
.app-shell::after {
  content: '';
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 200;
  background: repeating-linear-gradient(
    to bottom,
    rgba(0, 0, 0, 0) 0px,
    rgba(0, 0, 0, 0) 2px,
    rgba(0, 0, 0, 0.22) 3px,
    rgba(0, 0, 0, 0.22) 4px
  );
}

.app-main {
  display: flex;
  flex-direction: column;
  /* Required: without it a wide table stretches the grid column past the
     viewport and puts a horizontal scrollbar on <body>. */
  min-width: 0;
}

.app-content {
  flex: 1;
  width: 100%;
  max-width: 1500px;
  margin: 0 auto;
  padding: var(--space-5) var(--space-6);
}

/* ---------------------------------------------------------------------------
   Screen header — a title line the way a 3270 panel names itself
   --------------------------------------------------------------------------- */

.page-header {
  margin-bottom: var(--space-5);
  padding-bottom: var(--space-3);
  border-bottom: 1px solid var(--border);
}

.page-header h2 {
  font-size: 1.125rem;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--accent);
  text-shadow: var(--glow-bright);
}

.page-header h2::before {
  content: '== ';
  color: var(--text-faint);
}

.page-header h2::after {
  content: ' ==';
  color: var(--text-faint);
}

.page-header p {
  color: var(--text-faint);
  font-size: 0.75rem;
  margin-top: var(--space-2);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

/* ---------------------------------------------------------------------------
   Panels
   --------------------------------------------------------------------------- */

.card {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  margin-bottom: var(--space-5);
}

.card-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--space-4);
  padding: var(--space-2) var(--space-4);
  border-bottom: 1px solid var(--border);
  background: var(--bg-sunk);
  flex-wrap: wrap;
}

.card-title {
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--accent);
}

/* Field marker, the way a panel labels a section. */
.card-title::before {
  /* \00A0 rather than a literal space: a plain space would terminate the
     escape sequence instead of rendering, gluing the marker to the label. */
  content: '\25B8\00A0';
  color: var(--text-faint);
}

.card > *:not(.card-header):not(.table-container):not(table) {
  padding-left: var(--space-4);
  padding-right: var(--space-4);
}
.card > *:not(.card-header):not(.table-container):not(table):first-child { padding-top: var(--space-4); }
.card > *:not(.card-header):not(.table-container):not(table):last-child { padding-bottom: var(--space-4); }

/* ---------------------------------------------------------------------------
   Value tiles
   --------------------------------------------------------------------------- */

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(212px, 1fr));
  gap: var(--space-4);
  margin-bottom: var(--space-5);
}

.stat-card {
  position: relative;
  background: var(--bg-surface);
  border: 1px solid var(--border);
  padding: var(--space-3) var(--space-4);
}

/* Intensity bar, recoloured by the status modifier classes the views pass. */
.stat-card::before {
  content: '';
  position: absolute;
  inset: 0 0 auto 0;
  height: 1px;
  background: var(--accent);
}

.stat-card.success::before { background: var(--green); }
.stat-card.info::before    { background: var(--blue); }
.stat-card.warning::before { background: var(--amber); }
.stat-card.danger::before  { background: var(--red); }

.stat-label {
  font-size: 0.625rem;
  font-weight: 500;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--text-faint);
  margin-bottom: var(--space-2);
}

.stat-label::after {
  content: ':';
  color: var(--text-dim);
}

.stat-value {
  font-size: 1.375rem;
  font-weight: 600;
  letter-spacing: 0.02em;
  color: var(--accent);
  line-height: 1.15;
  font-variant-numeric: tabular-nums;
  text-shadow: var(--glow-bright);
}

.stat-card.success .stat-value { color: var(--green-deep); }
.stat-card.info .stat-value    { color: var(--blue-deep); }
.stat-card.warning .stat-value { color: var(--amber-deep); }
.stat-card.danger .stat-value  { color: var(--red-deep); }

/* ---------------------------------------------------------------------------
   Tables — the core of any terminal screen
   --------------------------------------------------------------------------- */

.table-container { overflow-x: auto; }

table {
  width: 100%;
  border-collapse: collapse;
}

thead { background: var(--bg-sunk); }

thead th {
  padding: var(--space-2) var(--space-3);
  font-size: 0.625rem;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--text-faint);
  text-align: left;
  white-space: nowrap;
  border-bottom: 1px solid var(--border-strong);
}

tbody td {
  padding: 0.3rem var(--space-3);
  border-bottom: 1px solid rgba(28, 83, 37, 0.5);
  font-size: 0.75rem;
  color: var(--text-soft);
  height: 30px;
  font-variant-numeric: tabular-nums;
  letter-spacing: 0.02em;
}

tbody tr:last-child td { border-bottom: 0; }

/* Row cursor. A real terminal inverted the selected line; this is the
   restrained version — bright phosphor on a lit background. */
tbody tr:hover td {
  background: var(--accent-dim);
  color: var(--accent);
}

tbody td strong {
  color: var(--text);
  font-weight: 600;
}

tbody tr:hover td strong { color: var(--accent-bright); }

/* ---------------------------------------------------------------------------
   Status fields — bracketed, the way a terminal renders an enumerated value
   --------------------------------------------------------------------------- */

.badge {
  display: inline-block;
  padding: 0;
  border: 0;
  background: none;
  font-size: 0.6875rem;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  white-space: nowrap;
}

.badge::before { content: '['; opacity: 0.55; }
.badge::after  { content: ']'; opacity: 0.55; }

.badge.success, .badge.increasing { color: var(--green-deep); }
.badge.info, .badge.stable        { color: var(--blue-deep); }
.badge.warning, .badge.medium     { color: var(--amber-deep); }
.badge.danger, .badge.high, .badge.decreasing { color: var(--red-deep); }
.badge.low { color: var(--text-faint); }

/* ---------------------------------------------------------------------------
   Controls
   --------------------------------------------------------------------------- */

button, select, input, textarea {
  font-family: var(--font-ui);
  letter-spacing: 0.04em;
}

/* Checkboxes and range thumbs default to the OS accent, which paints system
   blue onto a phosphor screen. Force them to the terminal's own colour. */
input[type="checkbox"],
input[type="radio"],
input[type="range"] {
  accent-color: var(--accent);
}

/* ---------------------------------------------------------------------------
   States
   --------------------------------------------------------------------------- */

.loading, .error {
  padding: var(--space-5);
  text-align: center;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--text-faint);
  background: var(--bg-surface);
  border: 1px solid var(--border);
}

.loading::after {
  content: ' \2588';
  animation: cursor-blink 1.06s steps(1) infinite;
}

.error {
  color: var(--red-deep);
  border-color: var(--red-border);
  background: var(--red-soft);
}

@keyframes cursor-blink {
  0%, 49% { opacity: 1; }
  50%, 100% { opacity: 0; }
}

/* ---------------------------------------------------------------------------
   Focus — the terminal's field cursor
   --------------------------------------------------------------------------- */

a:focus-visible,
button:focus-visible,
select:focus-visible,
input:focus-visible {
  outline: 1px solid var(--accent-bright);
  outline-offset: 1px;
}

/* ---------------------------------------------------------------------------
   Status line — pinned to the foot of the screen, as a 3270 operator
   information area would be
   --------------------------------------------------------------------------- */

.status-line {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  flex-wrap: wrap;
  padding: var(--space-2) var(--space-6);
  border-top: 1px solid var(--border);
  background: var(--bg-sunk);
  font-size: 0.625rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--text-faint);
}

.status-line .field { white-space: nowrap; }
.status-line .field b { color: var(--text); font-weight: 600; }
.status-line .ready { margin-left: auto; color: var(--accent); }

.status-line .cursor {
  display: inline-block;
  animation: cursor-blink 1.06s steps(1) infinite;
}

/* ---------------------------------------------------------------------------
   Responsive
   --------------------------------------------------------------------------- */

@media (max-width: 1024px) {
  .app-shell,
  .app-shell.is-collapsed { grid-template-columns: var(--sidebar-w-collapsed) 1fr; }
  .app-content { padding: var(--space-4) var(--space-5); }
  .status-line { padding-left: var(--space-5); padding-right: var(--space-5); }
}

@media (max-width: 768px) {
  .app-shell,
  .app-shell.is-collapsed { grid-template-columns: 1fr; }
  .app-content { padding: var(--space-4) var(--space-4) 5rem; }
  .status-line { display: none; }
}

@media (prefers-reduced-motion: reduce) {
  .app-shell { transition: none; }
  .loading::after,
  .status-line .cursor { animation: none; }
}
</style>
