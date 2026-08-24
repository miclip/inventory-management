<template>
  <div class="inventory">
    <div class="page-header">
      <h2>{{ t('inventory.title') }}</h2>
      <p>{{ t('inventory.description') }}</p>
    </div>

    <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else>
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('inventory.stockLevels') }} ({{ filteredItems.length }} {{ t('inventory.skus') }})</h3>
          <span v-if="atRiskCount > 0" class="at-risk-count" :title="t('coverage.atRiskHint')">
            {{ atRiskCount }} {{ t('coverage.atRisk') }}
          </span>
          <div class="search-box">
            <svg class="search-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clip-rule="evenodd" />
            </svg>
            <input
              v-model="searchQuery"
              type="text"
              :placeholder="t('inventory.searchPlaceholder')"
              class="search-input"
            />
            <button
              v-if="searchQuery"
              @click="searchQuery = ''"
              class="clear-search"
              :title="t('inventory.clearSearch')"
            >
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
              </svg>
            </button>
          </div>
        </div>
        <div class="table-container">
          <table>
            <thead>
              <tr>
                <th>{{ t('inventory.table.sku') }}</th>
                <th>{{ t('inventory.table.itemName') }}</th>
                <th>{{ t('inventory.table.category') }}</th>
                <th>{{ t('inventory.table.quantityOnHand') }}</th>
                <th>{{ t('inventory.table.reorderPoint') }}</th>
                <th class="num">{{ t('coverage.daysCover') }}</th>
                <th class="num">{{ t('coverage.leadTime') }}</th>
                <th>{{ t('coverage.risk') }}</th>
                <th class="num">{{ t('coverage.reorderQty') }}</th>
                <th>{{ t('inventory.table.unitCost') }}</th>
                <th>{{ t('inventory.table.totalValue') }}</th>
                <th>{{ t('inventory.table.location') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="item in filteredItems"
                :key="item.sku"
                class="clickable-row"
                @click="showItemDetail(item)"
              >
                <td><strong>{{ item.sku }}</strong></td>
                <td>{{ translateProductName(item.name) }}</td>
                <td>{{ translateCategory(item.category) }}</td>
                <td><strong>{{ item.quantity_on_hand }}</strong></td>
                <td>{{ item.reorder_point }}</td>
                <td class="num" :class="coverClass(item)">{{ formatCover(item) }}</td>
                <td class="num">{{ t('coverage.days', { days: item.lead_time_days }) }}</td>
                <td>
                  <span :class="['badge', riskClass(item.risk)]">{{ t(`coverage.level.${item.risk}`) }}</span>
                </td>
                <td class="num">
                  <strong v-if="item.shortfall_at_lead_time > 0">
                    {{ item.shortfall_at_lead_time.toLocaleString() }}
                  </strong>
                  <span v-else class="dim">&mdash;</span>
                </td>
                <td>{{ currencySymbol }}{{ item.unit_cost.toFixed(2) }}</td>
                <td><strong>{{ currencySymbol }}{{ (item.quantity_on_hand * item.unit_cost).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2}) }}</strong></td>
                <td>{{ translateWarehouse(item.location) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <InventoryDetailModal
      :is-open="showItemModal"
      :inventory-item="selectedItem"
      @close="showItemModal = false"
    />
  </div>
</template>

<script>
import { ref, onMounted, watch, computed } from 'vue'
import { api } from '../api'
import { useFilters } from '../composables/useFilters'
import { useI18n } from '../composables/useI18n'
import InventoryDetailModal from '../components/InventoryDetailModal.vue'

export default {
  name: 'Inventory',
  components: {
    InventoryDetailModal
  },
  setup() {
    const { t, currentCurrency, translateProductName, translateWarehouse } = useI18n()

    const currencySymbol = computed(() => {
      return currentCurrency.value === 'JPY' ? '¥' : '$'
    })

    const loading = ref(true)
    const error = ref(null)
    const items = ref([])
    const searchQuery = ref('')

    // Modal state
    const showItemModal = ref(false)
    const selectedItem = ref(null)

    // Use shared filters
    const { selectedLocation, selectedCategory, getCurrentFilters } = useFilters()

    // Worst risk first. The server already returns rows in this order; the
    // map is here because the search filter re-sorts client-side.
    const RISK_ORDER = { stockout: 0, critical: 1, warning: 2, ok: 3, idle: 4 }

    // An item is genuinely at risk when it will run dry before a replacement
    // can land — not merely when it dips below its reorder point, which knows
    // nothing about how long resupply takes.
    const atRiskCount = computed(() =>
      items.value.filter(i => i.risk === 'stockout' || i.risk === 'critical').length
    )

    const formatCover = (item) => {
      if (item.days_of_cover === null) return t('coverage.unbounded')
      return t('coverage.days', { days: item.days_of_cover.toFixed(1) })
    }

    const coverClass = (item) => {
      if (item.risk === 'stockout' || item.risk === 'critical') return 'cover-critical'
      if (item.risk === 'warning') return 'cover-warning'
      return ''
    }

    const riskClass = (risk) => {
      const map = { stockout: 'danger', critical: 'danger', warning: 'warning', ok: 'success', idle: 'low' }
      return map[risk] || 'low'
    }

    // Computed property to filter items by search query and sort by stock status
    const filteredItems = computed(() => {
      let filtered = items.value

      // Apply search filter if query exists
      if (searchQuery.value.trim()) {
        const query = searchQuery.value.toLowerCase().trim()
        filtered = filtered.filter(item =>
          item.name.toLowerCase().includes(query)
        )
      }

      // Worst risk first, then least cover. Copy before sorting so the source
      // ref is not mutated.
      return filtered.slice().sort((a, b) => {
        const byRisk = RISK_ORDER[a.risk] - RISK_ORDER[b.risk]
        if (byRisk !== 0) return byRisk
        const coverA = a.days_of_cover === null ? Infinity : a.days_of_cover
        const coverB = b.days_of_cover === null ? Infinity : b.days_of_cover
        return coverA - coverB
      })
    })

    const loadInventory = async () => {
      try {
        loading.value = true
        const filters = getCurrentFilters()
        // The coverage endpoint returns every inventory field plus the
        // days-of-cover metrics, so it replaces the plain inventory call.
        items.value = await api.getInventoryCoverage({
          warehouse: filters.warehouse,
          category: filters.category
        })
      } catch (err) {
        error.value = 'Failed to load inventory: ' + err.message
      } finally {
        loading.value = false
      }
    }

    // Watch for filter changes and reload data
    watch([selectedLocation, selectedCategory], () => {
      loadInventory()
    })

    const translateCategory = (category) => {
      const categoryMap = {
        'Circuit Boards': t('categories.circuitBoards'),
        'Sensors': t('categories.sensors'),
        'Actuators': t('categories.actuators'),
        'Controllers': t('categories.controllers'),
        'Power Supplies': t('categories.powerSupplies')
      }
      return categoryMap[category] || category
    }

    const showItemDetail = (item) => {
      selectedItem.value = item
      showItemModal.value = true
    }

    onMounted(loadInventory)

    return {
      t,
      loading,
      error,
      items,
      searchQuery,
      filteredItems,
      atRiskCount,
      formatCover,
      coverClass,
      riskClass,
      translateCategory,
      showItemModal,
      selectedItem,
      showItemDetail,
      currencySymbol,
      translateProductName,
      translateWarehouse
    }
  }
}
</script>

<style scoped>
.num {
  text-align: right;
  font-variant-numeric: tabular-nums;
}

th.num { text-align: right; }

/* Cover shorter than the lead time is the alarm condition. */
.cover-critical { color: var(--red-deep); font-weight: 600; }
.cover-warning { color: var(--amber-deep); font-weight: 600; }

.dim { color: var(--text-dim); }

.at-risk-count {
  font-size: 0.625rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--red-deep);
  border: 1px solid var(--red-border);
  padding: 0.1rem var(--space-2);
  white-space: nowrap;
}

.page-header {
  margin-bottom: 1.5rem;
}

.page-header h2 {
  margin-bottom: 0.25rem;
}

.page-header p {
  color: var(--text-faint);
  font-size: 0.875rem;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1.5rem;
  padding: 1.25rem 1.5rem;
  border-bottom: 1px solid var(--border);
}

.card-title {
  font-size: 1rem;
  font-weight: 600;
  color: var(--text);
  margin: 0;
}

.search-box {
  position: relative;
  display: flex;
  align-items: center;
  min-width: 300px;
}

.search-icon {
  position: absolute;
  left: 0.75rem;
  width: 18px;
  height: 18px;
  color: var(--text-dim);
  pointer-events: none;
}

.search-input {
  width: 100%;
  padding: 0.5rem 2.5rem 0.5rem 2.5rem;
  border: 1px solid var(--border-strong);
  font-size: 0.875rem;
  color: var(--text);
  background: var(--bg-sunk);
  transition: all 0.2s;
}

.search-input:focus {
  outline: none;
  border-color: var(--accent);
  background: var(--bg-surface);
}

.search-input::placeholder {
  color: var(--text-dim);
}

.clear-search {
  position: absolute;
  right: 0.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0.25rem;
  background: transparent;
  border: none;
  color: var(--text-dim);
  cursor: pointer;
  transition: all 0.2s;
}

.clear-search:hover {
  background: var(--border);
  color: var(--text-faint);
}

.clear-search svg {
  width: 18px;
  height: 18px;
}

.loading,
.error {
  padding: 2rem;
  text-align: center;
  color: var(--text-faint);
}

.error {
  color: var(--red);
}

.clickable-row {
  cursor: pointer;
  transition: background-color 0.15s ease;
}

.clickable-row:hover {
  background: var(--accent-soft) !important;
}
</style>
