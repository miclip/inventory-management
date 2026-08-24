<template>
  <div class="restocking">
    <div class="page-header">
      <h2>{{ t('restocking.title') }}</h2>
      <p>{{ t('restocking.description') }}</p>
    </div>

    <!-- Budget control -->
    <div class="card budget-card">
      <div class="budget-head">
        <div>
          <div class="budget-label">{{ t('restocking.budget') }}</div>
          <div class="budget-amount">{{ formatMoney(budget) }}</div>
          <div class="budget-hint">{{ t('restocking.budgetHint') }}</div>
        </div>
        <div class="budget-readout">
          <div class="readout">
            <span class="readout-label">{{ t('restocking.allocated') }}</span>
            <span class="readout-value">{{ formatMoney(selectedTotal) }}</span>
          </div>
          <div class="readout">
            <span class="readout-label">{{ t('restocking.remaining') }}</span>
            <span :class="['readout-value', { negative: isOverBudget }]">
              {{ formatMoney(budget - selectedTotal) }}
            </span>
          </div>
          <div class="readout">
            <span class="readout-label">{{ t('restocking.totalNeed') }}</span>
            <span class="readout-value muted">{{ formatMoney(totalNeed) }}</span>
          </div>
        </div>
      </div>

      <input
        type="range"
        class="budget-slider"
        :min="BUDGET_MIN"
        :max="BUDGET_MAX"
        :step="BUDGET_STEP"
        v-model.number="budget"
      />
      <div class="slider-scale">
        <span>{{ formatCompact(BUDGET_MIN) }}</span>
        <span>{{ formatCompact(BUDGET_MAX) }}</span>
      </div>

      <!-- Utilisation bar: green while inside budget, red once the manual
           quantity edits push the selection past it. -->
      <div class="usage-track">
        <div
          class="usage-fill"
          :class="{ over: isOverBudget }"
          :style="{ width: usagePercent + '%' }"
        ></div>
      </div>
    </div>

    <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="error">{{ error }}</div>

    <template v-else>
      <div v-if="submitMessage" class="submit-banner">{{ submitMessage }}</div>

      <!-- Recommended basket -->
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('restocking.recommended') }}</h3>
          <span class="selection-count">
            {{ t('restocking.itemsSelected', { count: selectedRows.length, total: rows.length }) }}
          </span>
        </div>

        <div v-if="rows.length === 0" class="empty-state">
          {{ t('restocking.noRecommendations') }}
        </div>

        <template v-else>
          <div class="table-container">
            <table class="restock-table">
              <thead>
                <tr>
                  <th class="col-include">{{ t('restocking.include') }}</th>
                  <th class="col-item">{{ t('inventory.table.itemName') }}</th>
                  <th class="col-num">{{ t('restocking.onHand') }}</th>
                  <th class="col-num">{{ t('restocking.forecast') }}</th>
                  <th class="col-num">{{ t('restocking.shortfall') }}</th>
                  <th class="col-qty">{{ t('restocking.orderQty') }}</th>
                  <th class="col-num">{{ t('restocking.lineTotal') }}</th>
                  <th class="col-lead">{{ t('restocking.leadTime') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in rows" :key="row.sku" :class="{ excluded: !row.included }">
                  <td class="col-include">
                    <input type="checkbox" v-model="row.included" :aria-label="row.sku" />
                  </td>
                  <td class="col-item">
                    <div class="item-name">{{ translateProductName(row.name) }}</div>
                    <div class="item-sub">
                      <span class="sku">{{ row.sku }}</span>
                      <span :class="['badge', urgencyClass(row.urgency)]">{{ t(`restocking.urgency.${row.urgency}`) }}</span>
                      <span class="warehouse">{{ translateWarehouse(row.warehouse) }}</span>
                    </div>
                    <div class="item-source" :title="t(`restocking.source.${row.demand_source}`)">
                      {{ t(`restocking.source.${row.demand_source}`) }}
                    </div>
                  </td>
                  <td class="col-num">{{ row.quantity_on_hand.toLocaleString() }}</td>
                  <td class="col-num">{{ row.forecasted_demand.toLocaleString() }}</td>
                  <td class="col-num strong">{{ row.shortfall.toLocaleString() }}</td>
                  <td class="col-qty">
                    <input
                      type="number"
                      class="qty-input"
                      min="0"
                      :max="row.shortfall"
                      :disabled="!row.included"
                      v-model.number="row.quantity"
                      @input="clampQuantity(row)"
                      :aria-label="`${row.sku} quantity`"
                    />
                  </td>
                  <td class="col-num strong">{{ formatMoney(lineTotal(row)) }}</td>
                  <td class="col-lead">{{ t('restocking.leadTimeDays', { days: row.lead_time_days }) }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div class="order-footer">
            <div class="footer-summary">
              <span v-if="isOverBudget" class="over-warning">
                {{ t('restocking.overBudget', { amount: formatMoney(selectedTotal - budget) }) }}
              </span>
              <span v-else-if="selectedRows.length === 0" class="footer-hint">
                {{ t('restocking.nothingSelected') }}
              </span>
              <span v-else class="footer-hint">
                {{ t('restocking.leadTime') }}:
                {{ t('restocking.leadTimeDays', { days: orderLeadTime }) }}
              </span>
            </div>
            <button
              class="place-order-btn"
              :disabled="!canPlaceOrder"
              @click="placeOrder"
            >
              {{ submitting ? t('restocking.placingOrder') : t('restocking.placeOrder') }}
            </button>
          </div>
        </template>
      </div>

      <!-- What the budget could not cover -->
      <div v-if="deferred.length" class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('restocking.deferred') }} ({{ deferred.length }})</h3>
          <span class="selection-count">{{ t('restocking.deferredHint') }}</span>
        </div>
        <div class="table-container">
          <table class="restock-table deferred-table">
            <thead>
              <tr>
                <th class="col-item">{{ t('inventory.table.itemName') }}</th>
                <th class="col-num">{{ t('restocking.onHand') }}</th>
                <th class="col-num">{{ t('restocking.shortfall') }}</th>
                <th class="col-num">{{ t('restocking.lineTotal') }}</th>
                <th class="col-lead">{{ t('restocking.leadTime') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in deferred" :key="row.sku">
                <td class="col-item">
                  <div class="item-name">{{ translateProductName(row.name) }}</div>
                  <div class="item-sub">
                    <span class="sku">{{ row.sku }}</span>
                    <span :class="['badge', urgencyClass(row.urgency)]">{{ t(`restocking.urgency.${row.urgency}`) }}</span>
                  </div>
                </td>
                <td class="col-num">{{ row.quantity_on_hand.toLocaleString() }}</td>
                <td class="col-num strong">{{ row.shortfall.toLocaleString() }}</td>
                <td class="col-num muted">{{ formatMoney(row.line_total) }}</td>
                <td class="col-lead">{{ t('restocking.leadTimeDays', { days: row.lead_time_days }) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>
  </div>
</template>

<script>
import { ref, computed, watch, onMounted } from 'vue'
import { api } from '../api'
import { useFilters } from '../composables/useFilters'
import { useI18n } from '../composables/useI18n'
import { formatCurrency, convertAmount } from '../utils/currency'

// Slider bounds. The max is a little above the ~$1.8M it costs to clear every
// shortfall in the fixture data, so the top of the range can fund everything.
const BUDGET_MIN = 10000
const BUDGET_MAX = 2000000
const BUDGET_STEP = 10000
const BUDGET_DEFAULT = 250000

export default {
  name: 'Restocking',
  setup() {
    const { t, currentCurrency, translateProductName, translateWarehouse } = useI18n()
    const { selectedLocation, selectedCategory, getCurrentFilters } = useFilters()

    const loading = ref(true)
    const error = ref(null)
    const submitting = ref(false)
    const submitMessage = ref('')
    const budget = ref(BUDGET_DEFAULT)
    const totalNeed = ref(0)
    const deferred = ref([])

    // Editable basket. Each row is the server's recommendation plus the two
    // fields the user controls: `included` and `quantity`.
    const rows = ref([])

    const loadRecommendations = async () => {
      try {
        loading.value = true
        error.value = null
        const filters = getCurrentFilters()
        const data = await api.getRestockingRecommendations(budget.value, filters)

        rows.value = data.recommended.map(item => ({
          ...item,
          included: true,
          quantity: item.recommended_quantity
        }))
        deferred.value = data.deferred
        totalNeed.value = data.total_need
      } catch (err) {
        error.value = 'Failed to load restocking recommendations: ' + err.message
      } finally {
        loading.value = false
      }
    }

    const selectedRows = computed(() =>
      rows.value.filter(row => row.included && row.quantity > 0)
    )

    // The `max` attribute only bounds the spinner arrows, so typed and pasted
    // values need clamping too. Blank input reads back as an empty string
    // rather than a number, which would make the line total NaN.
    const clampQuantity = (row) => {
      const quantity = Number(row.quantity)
      if (!Number.isFinite(quantity) || quantity < 0) {
        row.quantity = 0
      } else if (quantity > row.shortfall) {
        row.quantity = row.shortfall
      }
    }

    const lineTotal = (row) => {
      if (!row.included || !row.quantity) return 0
      return row.quantity * row.unit_cost
    }

    const selectedTotal = computed(() =>
      selectedRows.value.reduce((sum, row) => sum + row.quantity * row.unit_cost, 0)
    )

    const isOverBudget = computed(() => selectedTotal.value > budget.value)

    const usagePercent = computed(() => {
      if (budget.value <= 0) return 0
      return Math.min(100, (selectedTotal.value / budget.value) * 100)
    })

    // The order ships complete, so it inherits its slowest line item's lead
    // time — the same rule the server applies when it stamps the order.
    const orderLeadTime = computed(() => {
      if (selectedRows.value.length === 0) return 0
      return Math.max(...selectedRows.value.map(row => row.lead_time_days))
    })

    const canPlaceOrder = computed(() =>
      selectedRows.value.length > 0 && !isOverBudget.value && !submitting.value
    )

    const placeOrder = async () => {
      if (!canPlaceOrder.value) return
      try {
        submitting.value = true
        submitMessage.value = ''
        const order = await api.createRestockingOrder({
          items: selectedRows.value.map(row => ({ sku: row.sku, quantity: row.quantity })),
          budget: budget.value
        })
        submitMessage.value = t('restocking.orderPlaced', {
          orderNumber: order.order_number,
          date: formatDate(order.expected_delivery)
        })
        // Re-pull so the basket reflects the budget again from a clean slate.
        await loadRecommendations()
      } catch (err) {
        error.value = 'Failed to submit order: ' + (err.response?.data?.detail || err.message)
      } finally {
        submitting.value = false
      }
    }

    const formatDate = (value) => {
      const date = new Date(value)
      if (isNaN(date.getTime())) return value
      const locale = currentCurrency.value === 'JPY' ? 'ja-JP' : 'en-US'
      return date.toLocaleDateString(locale, { year: 'numeric', month: 'short', day: 'numeric' })
    }

    // All fixture prices are USD; formatCurrency converts when the locale is ja.
    const formatMoney = (amount) => formatCurrency(amount, currentCurrency.value)

    const formatCompact = (amount) => {
      const value = convertAmount(amount, currentCurrency.value)
      const symbol = currentCurrency.value === 'JPY' ? '¥' : '$'
      if (Math.abs(value) >= 1000000) return `${symbol}${(value / 1000000).toFixed(1)}M`
      return `${symbol}${Math.round(value / 1000)}K`
    }

    const urgencyClass = (urgency) => {
      const map = { critical: 'danger', high: 'warning', moderate: 'info' }
      return map[urgency] || 'info'
    }

    // Reloading on budget change is what makes the slider feel live. Only the
    // warehouse and category filters matter here — restocking has no time or
    // order-status dimension.
    watch([budget, selectedLocation, selectedCategory], loadRecommendations)

    onMounted(loadRecommendations)

    return {
      BUDGET_MIN,
      BUDGET_MAX,
      BUDGET_STEP,
      t,
      loading,
      error,
      submitting,
      submitMessage,
      budget,
      rows,
      deferred,
      totalNeed,
      selectedRows,
      selectedTotal,
      isOverBudget,
      usagePercent,
      orderLeadTime,
      canPlaceOrder,
      lineTotal,
      clampQuantity,
      placeOrder,
      formatMoney,
      formatCompact,
      urgencyClass,
      translateProductName,
      translateWarehouse
    }
  }
}
</script>

<style scoped>
/* ---------- budget control ---------- */

.budget-card {
  padding: 1.5rem;
  margin-bottom: 1.5rem;
}

.budget-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 2rem;
  flex-wrap: wrap;
  margin-bottom: 1.25rem;
}

.budget-label {
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--text-faint);
  margin-bottom: 0.35rem;
}

.budget-amount {
  font-size: 2rem;
  font-weight: 600;
  color: var(--text);
  line-height: 1.1;
  font-variant-numeric: tabular-nums;
}

.budget-hint {
  font-size: 0.813rem;
  color: var(--text-faint);
  margin-top: 0.35rem;
}

.budget-readout {
  display: flex;
  gap: 2rem;
  flex-wrap: wrap;
}

.readout {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.readout-label {
  font-size: 0.75rem;
  color: var(--text-faint);
  white-space: nowrap;
}

.readout-value {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--text);
  font-variant-numeric: tabular-nums;
}

.readout-value.negative { color: var(--red); }
.readout-value.muted { color: var(--text-faint); font-weight: 500; }

/* ---------- slider ---------- */

.budget-slider {
  width: 100%;
  -webkit-appearance: none;
  appearance: none;
  height: 6px;
  background: var(--border);
  outline: none;
  cursor: pointer;
}

.budget-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 20px;
  height: 20px;
  background: var(--text);
  border: 2px solid var(--bg-surface);
  cursor: pointer;
}

.budget-slider::-moz-range-thumb {
  width: 18px;
  height: 18px;
  background: var(--text);
  border: 2px solid var(--bg-surface);
  cursor: pointer;
}

.budget-slider:focus-visible {
}

.slider-scale {
  display: flex;
  justify-content: space-between;
  font-size: 0.75rem;
  color: var(--text-dim);
  margin-top: 0.4rem;
  font-variant-numeric: tabular-nums;
}

.usage-track {
  height: 4px;
  background: var(--bg-sunk);
  overflow: hidden;
  margin-top: 1rem;
}

.usage-fill {
  height: 100%;
  background: var(--green);
  transition: width 0.15s ease;
}

.usage-fill.over { background: var(--red); }

/* ---------- table ---------- */

.restock-table {
  width: 100%;
  table-layout: fixed;
}

.col-include { width: 64px; text-align: center; }
.col-item { width: auto; min-width: 260px; }
.col-num { width: 110px; text-align: right; }
.col-qty { width: 118px; text-align: right; }
.col-lead { width: 110px; }

.restock-table th.col-num,
.restock-table th.col-qty { text-align: right; }

tr.excluded { opacity: 0.45; }

.item-name {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--text);
  margin-bottom: 0.25rem;
}

.item-sub {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.sku {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.75rem;
  color: var(--text-faint);
}

.warehouse {
  font-size: 0.75rem;
  color: var(--text-faint);
}

.item-source {
  font-size: 0.688rem;
  color: var(--text-dim);
  margin-top: 0.25rem;
}

.col-num, .col-qty { font-variant-numeric: tabular-nums; }

.strong { font-weight: 600; color: var(--text); }
.muted { color: var(--text-faint); }

.qty-input {
  width: 100%;
  padding: 0.35rem 0.5rem;
  border: 1px solid var(--border-strong);
  font-size: 0.875rem;
  text-align: right;
  color: var(--text);
  background: var(--bg-surface);
  font-variant-numeric: tabular-nums;
}

.qty-input:focus {
  outline: none;
  border-color: var(--text);
}

.qty-input:disabled {
  background: var(--bg-sunk);
  color: var(--text-dim);
  cursor: not-allowed;
}

/* ---------- footer / actions ---------- */

.selection-count {
  font-size: 0.813rem;
  color: var(--text-faint);
}

.order-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1.5rem;
  padding: 1.25rem 1.5rem;
  border-top: 1px solid var(--border);
  background: var(--bg-sunk);
  flex-wrap: wrap;
}

.footer-hint { font-size: 0.875rem; color: var(--text-faint); }

.over-warning {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--red);
}

.place-order-btn {
  padding: 0.65rem 1.5rem;
  border: none;
  background: var(--text);
  color: var(--bg-surface);
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s ease;
}

.place-order-btn:hover:not(:disabled) { background: var(--text); }

.place-order-btn:disabled {
  background: var(--border-strong);
  color: var(--bg-surface);
  cursor: not-allowed;
}

.submit-banner {
  padding: 0.85rem 1.25rem;
  border: 1px solid var(--green-border);
  border-left: 3px solid var(--green);
  background: var(--green-soft);
  color: var(--green);
  font-size: 0.875rem;
  font-weight: 500;
  margin-bottom: 1.5rem;
}

.empty-state {
  padding: 2.5rem 1.5rem;
  text-align: center;
  color: var(--text-faint);
  font-size: 0.875rem;
}

.deferred-table .col-item { min-width: 240px; }
</style>
