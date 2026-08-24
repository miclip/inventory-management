from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from pydantic import BaseModel
from collections import defaultdict
from datetime import datetime, timedelta
from mock_data import inventory_items, orders, demand_forecasts, backlog_items, spending_summary, monthly_spending, category_spending, recent_transactions, purchase_orders

app = FastAPI(title="Factory Inventory Management System")

# Quarter mapping for date filtering
QUARTER_MAP = {
    'Q1-2025': ['2025-01', '2025-02', '2025-03'],
    'Q2-2025': ['2025-04', '2025-05', '2025-06'],
    'Q3-2025': ['2025-07', '2025-08', '2025-09'],
    'Q4-2025': ['2025-10', '2025-11', '2025-12']
}

def filter_by_month(items: list, month: Optional[str]) -> list:
    """Filter items by month/quarter based on order_date field"""
    if not month or month == 'all':
        return items

    if month.startswith('Q'):
        # Handle quarters
        if month in QUARTER_MAP:
            months = QUARTER_MAP[month]
            return [item for item in items if any(m in item.get('order_date', '') for m in months)]
    else:
        # Direct month match
        return [item for item in items if month in item.get('order_date', '')]

    return items

def apply_filters(items: list, warehouse: Optional[str] = None, category: Optional[str] = None,
                 status: Optional[str] = None) -> list:
    """Apply common filters to a list of items"""
    filtered = items

    if warehouse and warehouse != 'all':
        filtered = [item for item in filtered if item.get('warehouse') == warehouse]

    if category and category != 'all':
        filtered = [item for item in filtered if item.get('category', '').lower() == category.lower()]

    if status and status != 'all':
        filtered = [item for item in filtered if item.get('status', '').lower() == status.lower()]

    return filtered

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data models
class InventoryItem(BaseModel):
    id: str
    sku: str
    name: str
    category: str
    warehouse: str
    quantity_on_hand: int
    reorder_point: int
    unit_cost: float
    location: str
    last_updated: str

class Order(BaseModel):
    id: str
    order_number: str
    customer: str
    items: List[dict]
    status: str
    order_date: str
    expected_delivery: str
    total_value: float
    actual_delivery: Optional[str] = None
    warehouse: Optional[str] = None
    category: Optional[str] = None

class DemandForecast(BaseModel):
    id: str
    item_sku: str
    item_name: str
    current_demand: int
    forecasted_demand: int
    trend: str
    period: str

class BacklogItem(BaseModel):
    id: str
    order_id: str
    item_sku: str
    item_name: str
    quantity_needed: int
    quantity_available: int
    days_delayed: int
    priority: str
    has_purchase_order: Optional[bool] = False

class PurchaseOrder(BaseModel):
    id: str
    backlog_item_id: str
    supplier_name: str
    quantity: int
    unit_cost: float
    expected_delivery_date: str
    status: str
    created_date: str
    notes: Optional[str] = None

class CreatePurchaseOrderRequest(BaseModel):
    backlog_item_id: str
    supplier_name: str
    quantity: int
    unit_cost: float
    expected_delivery_date: str
    notes: Optional[str] = None

class InventoryCoverage(BaseModel):
    sku: str
    name: str
    category: str
    warehouse: str
    location: str
    quantity_on_hand: int
    reorder_point: int
    unit_cost: float
    forecasted_demand: int
    demand_source: str
    daily_demand: float
    # None means "unbounded": no demand signal, so the stock never depletes.
    days_of_cover: Optional[float] = None
    lead_time_days: int
    risk: str
    shortfall_at_lead_time: int
    below_reorder_point: bool

class RestockCandidate(BaseModel):
    sku: str
    name: str
    category: str
    warehouse: str
    unit_cost: float
    quantity_on_hand: int
    reorder_point: int
    forecasted_demand: int
    demand_source: str
    shortfall: int
    recommended_quantity: int
    line_total: float
    below_reorder_point: bool
    urgency: str
    lead_time_days: int
    daily_demand: float
    days_of_cover: Optional[float] = None
    risk: str

class RestockingRecommendations(BaseModel):
    budget: float
    recommended_spend: float
    remaining_budget: float
    total_need: float
    recommended: List[RestockCandidate]
    deferred: List[RestockCandidate]

class RestockingOrderItem(BaseModel):
    sku: str
    name: str
    category: str
    warehouse: str
    quantity: int
    unit_cost: float
    line_total: float
    lead_time_days: int

class RestockingOrder(BaseModel):
    id: str
    order_number: str
    status: str
    submitted_date: str
    expected_delivery: str
    lead_time_days: int
    item_count: int
    total_value: float
    total_units: int
    budget: Optional[float] = None
    notes: Optional[str] = None
    items: List[RestockingOrderItem]

class RestockingOrderItemRequest(BaseModel):
    sku: str
    quantity: int

class CreateRestockingOrderRequest(BaseModel):
    items: List[RestockingOrderItemRequest]
    budget: Optional[float] = None
    notes: Optional[str] = None

# API endpoints
@app.get("/")
def root():
    return {"message": "Factory Inventory Management System API", "version": "1.0.0"}

@app.get("/api/inventory", response_model=List[InventoryItem])
def get_inventory(
    warehouse: Optional[str] = None,
    category: Optional[str] = None
):
    """Get all inventory items with optional filtering"""
    return apply_filters(inventory_items, warehouse, category)

@app.get("/api/inventory/coverage", response_model=List[InventoryCoverage])
def get_inventory_coverage(
    warehouse: Optional[str] = None,
    category: Optional[str] = None
):
    """Days of stock cover per SKU, and the risk that implies.

    Declared before /api/inventory/{item_id} deliberately: Starlette matches
    routes in registration order, so putting this after the path-param route
    would make it resolve as item_id="coverage" and 404.
    """
    forecasts = _forecast_lookup()
    historical = _demand_from_order_history()
    rows = []

    for item in apply_filters(inventory_items, warehouse, category):
        demand, source = resolve_demand(item, forecasts, historical)
        cover = coverage_for_item(item, demand)
        rows.append({
            'sku': item['sku'],
            'name': item['name'],
            'category': item['category'],
            'warehouse': item['warehouse'],
            'location': item['location'],
            'quantity_on_hand': item['quantity_on_hand'],
            'reorder_point': item['reorder_point'],
            'unit_cost': item['unit_cost'],
            'forecasted_demand': demand,
            'demand_source': source,
            'below_reorder_point': item['quantity_on_hand'] <= item['reorder_point'],
            **cover,
        })

    # Most urgent first: worst risk, then least cover, then largest gap.
    rows.sort(key=lambda r: (
        RISK_ORDER[r['risk']],
        r['days_of_cover'] if r['days_of_cover'] is not None else float('inf'),
        -r['shortfall_at_lead_time'],
    ))
    return rows

@app.get("/api/inventory/{item_id}", response_model=InventoryItem)
def get_inventory_item(item_id: str):
    """Get a specific inventory item"""
    item = next((item for item in inventory_items if item["id"] == item_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

@app.get("/api/orders", response_model=List[Order])
def get_orders(
    warehouse: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    month: Optional[str] = None
):
    """Get all orders with optional filtering"""
    filtered_orders = apply_filters(orders, warehouse, category, status)
    filtered_orders = filter_by_month(filtered_orders, month)
    return filtered_orders

@app.get("/api/orders/{order_id}", response_model=Order)
def get_order(order_id: str):
    """Get a specific order"""
    order = next((order for order in orders if order["id"] == order_id), None)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order

@app.get("/api/demand", response_model=List[DemandForecast])
def get_demand_forecasts():
    """Get demand forecasts"""
    return demand_forecasts

@app.get("/api/backlog", response_model=List[BacklogItem])
def get_backlog():
    """Get backlog items with purchase order status"""
    # Add has_purchase_order flag to each backlog item
    result = []
    for item in backlog_items:
        item_dict = dict(item)
        # Check if this backlog item has a purchase order
        has_po = any(po["backlog_item_id"] == item["id"] for po in purchase_orders)
        item_dict["has_purchase_order"] = has_po
        result.append(item_dict)
    return result

@app.get("/api/dashboard/summary")
def get_dashboard_summary(
    warehouse: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    month: Optional[str] = None
):
    """Get summary statistics for dashboard with optional filtering"""
    # Filter inventory
    filtered_inventory = apply_filters(inventory_items, warehouse, category)

    # Filter orders
    filtered_orders = apply_filters(orders, warehouse, category, status)
    filtered_orders = filter_by_month(filtered_orders, month)

    total_inventory_value = sum(item["quantity_on_hand"] * item["unit_cost"] for item in filtered_inventory)
    low_stock_items = len([item for item in filtered_inventory if item["quantity_on_hand"] <= item["reorder_point"]])
    pending_orders = len([order for order in filtered_orders if order["status"] in ["Processing", "Backordered"]])
    total_backlog_items = len(backlog_items)

    return {
        "total_inventory_value": round(total_inventory_value, 2),
        "low_stock_items": low_stock_items,
        "pending_orders": pending_orders,
        "total_backlog_items": total_backlog_items,
        "total_orders_value": sum(order["total_value"] for order in filtered_orders)
    }

@app.get("/api/spending/summary")
def get_spending_summary():
    """Get spending summary statistics"""
    return spending_summary

@app.get("/api/spending/monthly")
def get_monthly_spending():
    """Get monthly spending breakdown"""
    return monthly_spending

@app.get("/api/spending/categories")
def get_category_spending():
    """Get spending by category"""
    return category_spending

@app.get("/api/spending/transactions")
def get_recent_transactions():
    """Get recent transactions"""
    return recent_transactions

def quarter_for_date(order_date: str) -> Optional[str]:
    """Map an order_date to its quarter key, or None if it matches no quarter.

    Derived from QUARTER_MAP so the quarter boundaries live in exactly one
    place; this previously duplicated them as an inline if/elif chain that had
    to be edited in tandem with the map.
    """
    for quarter, months in QUARTER_MAP.items():
        if any(month in order_date for month in months):
            return quarter
    return None


@app.get("/api/reports/quarterly")
def get_quarterly_reports(
    warehouse: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    month: Optional[str] = None
):
    """Get quarterly performance reports, honouring the global filters."""
    filtered_orders = apply_filters(orders, warehouse, category, status)
    filtered_orders = filter_by_month(filtered_orders, month)

    quarters = {}

    for order in filtered_orders:
        quarter = quarter_for_date(order.get('order_date', ''))
        if quarter is None:
            continue

        if quarter not in quarters:
            quarters[quarter] = {
                'quarter': quarter,
                'total_orders': 0,
                'total_revenue': 0,
                'delivered_orders': 0,
                'avg_order_value': 0,
                'fulfillment_rate': 0.0,
            }

        quarters[quarter]['total_orders'] += 1
        quarters[quarter]['total_revenue'] += order.get('total_value', 0)
        if order.get('status') == 'Delivered':
            quarters[quarter]['delivered_orders'] += 1

    result = []
    for data in quarters.values():
        # Always present, so the client never has to guard on a missing key.
        if data['total_orders'] > 0:
            data['avg_order_value'] = round(data['total_revenue'] / data['total_orders'], 2)
            data['fulfillment_rate'] = round((data['delivered_orders'] / data['total_orders']) * 100, 1)
        data['total_revenue'] = round(data['total_revenue'], 2)
        result.append(data)

    result.sort(key=lambda x: x['quarter'])
    return result

@app.get("/api/reports/monthly-trends")
def get_monthly_trends(
    warehouse: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    month: Optional[str] = None
):
    """Get month-over-month trends, honouring the global filters."""
    filtered_orders = apply_filters(orders, warehouse, category, status)
    filtered_orders = filter_by_month(filtered_orders, month)

    months = {}

    for order in filtered_orders:
        order_date = order.get('order_date', '')
        if not order_date:
            continue

        # Extract month (format: YYYY-MM-DD)
        month = order_date[:7]  # Gets YYYY-MM

        if month not in months:
            months[month] = {
                'month': month,
                'order_count': 0,
                'revenue': 0,
                'delivered_count': 0
            }

        months[month]['order_count'] += 1
        months[month]['revenue'] += order.get('total_value', 0)
        if order.get('status') == 'Delivered':
            months[month]['delivered_count'] += 1

    result = list(months.values())
    for data in result:
        data['revenue'] = round(data['revenue'], 2)
    result.sort(key=lambda x: x['month'])
    return result

# ---------------------------------------------------------------------------
# Restocking
# ---------------------------------------------------------------------------

# Supplier lead time in calendar days, keyed by lowercased inventory category.
# None of the JSON fixtures carry a lead-time field, so these are fixed
# per-category assumptions rather than data. An order's lead time is the MAX
# across its line items, because a restocking order ships complete rather than
# in per-item shipments.
LEAD_TIMES_BY_CATEGORY = {
    'circuit boards': 21,
    'sensors': 14,
    'actuators': 18,
    'controllers': 28,
    'power supplies': 10,
}
DEFAULT_LEAD_TIME_DAYS = 21

# Restocking orders submitted through the UI. In-memory like every other
# dataset here, so a server restart clears them.
submitted_restocking_orders: List[dict] = []


def lead_time_for_category(category: str) -> int:
    """Lead time in days for an inventory category, falling back to a default."""
    return LEAD_TIMES_BY_CATEGORY.get((category or '').lower(), DEFAULT_LEAD_TIME_DAYS)


# Both demand signals are 30-day figures — the curated forecast's period is
# "Next 30 days", and the order-history projection is per-month — so one
# divisor converts either to a daily rate.
DEMAND_PERIOD_DAYS = 30

# Slack above the lead time that still counts as comfortable. Below the lead
# time an item cannot be replenished before it runs dry; below this multiple it
# can, but with no room for a late shipment.
COVER_WARNING_FACTOR = 1.5

# Sort weight, worst first.
RISK_ORDER = {'stockout': 0, 'critical': 1, 'warning': 2, 'ok': 3, 'idle': 4}


def resolve_demand(item: dict, forecasts: dict, historical: dict):
    """30-day demand for an item, plus which signal produced it.

    The curated forecast wins where it can be matched (by SKU, then by product
    name); order history covers everything else. See _forecast_lookup for why
    the name fallback exists.
    """
    forecast_demand = forecasts.get(item['sku'], forecasts.get(item['name']))
    if forecast_demand is not None:
        return forecast_demand, 'forecast'
    return historical.get(item['sku'], 0), 'order_history'


def coverage_for_item(item: dict, demand: int) -> dict:
    """Days of stock remaining, and the risk that implies given the lead time.

    Days of cover against lead time is the operative reorder signal, and it is
    strictly better than the reorder point on its own: an item can sit ABOVE
    its reorder point and still be a guaranteed stockout, because the reorder
    point knows nothing about how long resupply takes. SRV-302 is the example
    in this dataset — 28 units against an 18-day actuator lead time.
    """
    on_hand = item['quantity_on_hand']
    lead_time = lead_time_for_category(item['category'])

    # Round the daily rate BEFORE deriving anything from it, so every number in
    # the response reconciles with every other one. Deriving cover from the
    # unrounded rate while publishing the rounded one leaves a client that
    # recomputes on_hand / daily_demand with a different answer than
    # days_of_cover, and puts rows whose rounded cover lands exactly on a
    # threshold into the wrong risk band.
    daily = round(demand / DEMAND_PERIOD_DAYS, 2) if demand else 0.0

    if daily <= 0:
        # No demand signal, so the stock never depletes and cover is unbounded.
        # Reported as null rather than a sentinel number, and flagged idle:
        # capital parked on a SKU nobody orders is its own kind of problem.
        return {
            'daily_demand': 0.0,
            'days_of_cover': None,
            'lead_time_days': lead_time,
            'risk': 'idle',
            'shortfall_at_lead_time': 0,
        }

    days_of_cover = round(on_hand / daily, 1)

    if on_hand <= 0:
        risk = 'stockout'
    elif days_of_cover < lead_time:
        risk = 'critical'
    elif days_of_cover < lead_time * COVER_WARNING_FACTOR:
        risk = 'warning'
    else:
        risk = 'ok'

    return {
        'daily_demand': daily,
        'days_of_cover': days_of_cover,
        'lead_time_days': lead_time,
        'risk': risk,
        # Units consumed over one lead time that are not on hand — the true
        # reorder quantity, as opposed to the gap to the reorder point.
        'shortfall_at_lead_time': max(0, round(daily * lead_time) - on_hand),
    }


def _forecast_lookup() -> dict:
    """Index demand_forecasts.json by both SKU and product name.

    Why both: the forecast fixture is keyed by its own SKU namespace, and only
    PSU-501 also exists in inventory.json. A second entry (SNR-420 /
    "Temperature Sensor Module") lines up with inventory item TMP-201 by
    product name only. Indexing on name as well as SKU lets the curated
    forecast win wherever it can be matched at all, instead of being discarded.
    """
    lookup = {}
    for forecast in demand_forecasts:
        demand = forecast.get('forecasted_demand', 0)
        lookup[forecast.get('item_sku', '')] = demand
        lookup[forecast.get('item_name', '')] = demand
    return lookup


def _demand_from_order_history() -> dict:
    """Project a 30-day demand figure per SKU from the order history.

    Sums the quantity ordered for each SKU across orders.json and divides by
    the number of distinct months present in that data, producing a per-month
    number comparable to the forecast fixture's "Next 30 days" period.

    This fallback exists because demand_forecasts.json only covers 1 of the 32
    inventory SKUs; without it almost nothing would ever be recommendable.
    """
    quantities = defaultdict(int)
    months = set()

    for order in orders:
        order_date = order.get('order_date', '')
        if order_date:
            months.add(order_date[:7])
        for item in order.get('items', []):
            quantities[item.get('sku', '')] += item.get('quantity', 0)

    month_count = len(months) or 1
    return {sku: round(total / month_count) for sku, total in quantities.items()}


def build_restock_candidates(warehouse: Optional[str] = None,
                             category: Optional[str] = None) -> List[dict]:
    """Every inventory item with unmet forecasted demand, most urgent first.

    Demand comes from the curated forecast where it can be matched, and from
    projected order history otherwise; demand_source records which was used so
    the UI can show the provenance. Sort order encodes the urgency-first
    policy, now keyed on days of cover against the supplier lead time rather
    than on the reorder point.
    """
    forecasts = _forecast_lookup()
    historical = _demand_from_order_history()
    candidates = []

    for item in apply_filters(inventory_items, warehouse, category):
        sku = item['sku']
        demand, source = resolve_demand(item, forecasts, historical)

        on_hand = item['quantity_on_hand']
        shortfall = max(0, demand - on_hand)
        if shortfall == 0:
            continue

        below_reorder = on_hand <= item['reorder_point']

        # Urgency now derives from days of cover against the lead time rather
        # than from the reorder point, so an item that will run dry before a
        # replacement can land ranks critical even when it is above its point.
        cover = coverage_for_item(item, demand)
        if cover['risk'] in ('stockout', 'critical'):
            urgency = 'critical'
        elif cover['risk'] == 'warning':
            urgency = 'high'
        else:
            urgency = 'moderate'

        candidates.append({
            'sku': sku,
            'name': item['name'],
            'category': item['category'],
            'warehouse': item['warehouse'],
            'unit_cost': item['unit_cost'],
            'quantity_on_hand': on_hand,
            'reorder_point': item['reorder_point'],
            'forecasted_demand': demand,
            'demand_source': source,
            'shortfall': shortfall,
            'recommended_quantity': 0,
            'line_total': 0.0,
            'below_reorder_point': below_reorder,
            'urgency': urgency,
            'lead_time_days': cover['lead_time_days'],
            'daily_demand': cover['daily_demand'],
            'days_of_cover': cover['days_of_cover'],
            'risk': cover['risk'],
        })

    # Urgency-first: worst risk leads, then the least cover, then the largest
    # shortfall. Items with no demand signal have unbounded cover and sort last.
    candidates.sort(key=lambda c: (
        RISK_ORDER[c['risk']],
        c['days_of_cover'] if c['days_of_cover'] is not None else float('inf'),
        -c['shortfall'],
    ))
    return candidates


@app.get("/api/restocking/recommendations", response_model=RestockingRecommendations)
def get_restocking_recommendations(
    budget: float = 250000,
    warehouse: Optional[str] = None,
    category: Optional[str] = None
):
    """Recommend which items to restock within a budget.

    Greedy over the urgency-ordered candidate list, taking each item's full
    shortfall when it fits. An item too expensive for the remaining budget is
    skipped rather than partially filled, and the walk continues — so a small
    budget still returns the cheaper items it can afford. Everything skipped is
    returned under `deferred` so the UI can show what the budget missed.
    """
    if budget < 0:
        raise HTTPException(status_code=400, detail="budget must not be negative")

    candidates = build_restock_candidates(warehouse, category)
    remaining = budget
    recommended = []
    deferred = []

    for candidate in candidates:
        line_total = round(candidate['shortfall'] * candidate['unit_cost'], 2)
        if line_total <= remaining:
            candidate['recommended_quantity'] = candidate['shortfall']
            candidate['line_total'] = line_total
            remaining = round(remaining - line_total, 2)
            recommended.append(candidate)
        else:
            # Surfaced so the user can see what a larger budget would cover.
            candidate['recommended_quantity'] = 0
            candidate['line_total'] = line_total
            deferred.append(candidate)

    return {
        'budget': round(budget, 2),
        'recommended_spend': round(budget - remaining, 2),
        'remaining_budget': remaining,
        # What it would cost to clear every shortfall, ignoring the budget.
        'total_need': round(sum(c['shortfall'] * c['unit_cost'] for c in candidates), 2),
        'recommended': recommended,
        'deferred': deferred,
    }


@app.get("/api/restocking-orders", response_model=List[RestockingOrder])
def list_restocking_orders():
    """Submitted restocking orders, newest first."""
    return list(reversed(submitted_restocking_orders))


@app.post("/api/restocking-orders", response_model=RestockingOrder, status_code=201)
def create_restocking_order(request: CreateRestockingOrderRequest):
    """Submit a restocking order.

    Line item details (name, category, warehouse, unit cost) are resolved
    server-side from inventory rather than trusted from the client, so a stale
    or tampered price cannot land in the order.
    """
    if not request.items:
        raise HTTPException(status_code=400, detail="Order must contain at least one item")

    inventory_by_sku = {item['sku']: item for item in inventory_items}
    order_items = []

    for line in request.items:
        if line.quantity <= 0:
            raise HTTPException(
                status_code=400,
                detail=f"Quantity for {line.sku} must be greater than zero"
            )

        item = inventory_by_sku.get(line.sku)
        if not item:
            raise HTTPException(status_code=404, detail=f"Unknown SKU: {line.sku}")

        order_items.append({
            'sku': item['sku'],
            'name': item['name'],
            'category': item['category'],
            'warehouse': item['warehouse'],
            'quantity': line.quantity,
            'unit_cost': item['unit_cost'],
            'line_total': round(line.quantity * item['unit_cost'], 2),
            'lead_time_days': lead_time_for_category(item['category']),
        })

    # The order ships complete, so its lead time is the slowest line item.
    lead_time_days = max(line['lead_time_days'] for line in order_items)
    submitted_at = datetime.now()

    order = {
        'id': str(len(submitted_restocking_orders) + 1),
        'order_number': f"RST-{submitted_at.year}-{len(submitted_restocking_orders) + 1:04d}",
        'status': 'Submitted',
        'submitted_date': submitted_at.isoformat(timespec='seconds'),
        'expected_delivery': (submitted_at + timedelta(days=lead_time_days)).isoformat(timespec='seconds'),
        'lead_time_days': lead_time_days,
        'item_count': len(order_items),
        'total_value': round(sum(line['line_total'] for line in order_items), 2),
        'total_units': sum(line['quantity'] for line in order_items),
        'budget': request.budget,
        'notes': request.notes,
        'items': order_items,
    }

    submitted_restocking_orders.append(order)
    return order


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
