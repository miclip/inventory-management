"""
Tests for reports API endpoints.
"""
import pytest


class TestQuarterlyReportsEndpoint:
    """Test suite for /api/reports/quarterly."""

    def test_get_quarterly_reports(self, client):
        """Test getting quarterly reports without filters."""
        response = client.get("/api/reports/quarterly")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

        first = data[0]
        assert "quarter" in first
        assert "total_orders" in first
        assert "total_revenue" in first
        assert "avg_order_value" in first
        assert "delivered_orders" in first
        assert "fulfillment_rate" in first

    def test_quarterly_reports_sorted_by_quarter(self, client):
        """Test that quarters come back in chronological order."""
        response = client.get("/api/reports/quarterly")
        data = response.json()

        quarters = [q["quarter"] for q in data]
        assert quarters == sorted(quarters)

    def test_quarterly_reports_field_types(self, client):
        """Test that quarterly report fields have proper numeric types."""
        response = client.get("/api/reports/quarterly")
        data = response.json()

        for quarter in data:
            assert isinstance(quarter["quarter"], str)
            assert isinstance(quarter["total_orders"], int)
            assert isinstance(quarter["total_revenue"], (int, float))
            assert isinstance(quarter["avg_order_value"], (int, float))
            assert isinstance(quarter["fulfillment_rate"], (int, float))
            assert quarter["total_orders"] > 0
            assert quarter["total_revenue"] >= 0
            assert 0 <= quarter["fulfillment_rate"] <= 100

    def test_quarterly_fulfillment_rate_always_present(self, client):
        """Test fulfillment_rate is always set, so clients need no fallback."""
        response = client.get("/api/reports/quarterly?warehouse=Tokyo")
        data = response.json()

        for quarter in data:
            assert quarter["fulfillment_rate"] is not None

    def test_quarterly_avg_order_value_calculation(self, client):
        """Test that avg_order_value equals revenue divided by order count."""
        response = client.get("/api/reports/quarterly")
        data = response.json()

        for quarter in data:
            expected = quarter["total_revenue"] / quarter["total_orders"]
            assert abs(quarter["avg_order_value"] - expected) < 0.01

    def test_quarterly_fulfillment_rate_calculation(self, client):
        """Test that fulfillment_rate equals delivered over total, as a percent."""
        response = client.get("/api/reports/quarterly")
        data = response.json()

        for quarter in data:
            expected = (quarter["delivered_orders"] / quarter["total_orders"]) * 100
            assert abs(quarter["fulfillment_rate"] - expected) < 0.1

    def test_quarterly_reports_by_warehouse(self, client):
        """Test filtering quarterly reports by warehouse."""
        unfiltered = client.get("/api/reports/quarterly").json()
        filtered = client.get("/api/reports/quarterly?warehouse=Tokyo").json()

        unfiltered_total = sum(q["total_orders"] for q in unfiltered)
        filtered_total = sum(q["total_orders"] for q in filtered)

        assert filtered_total > 0
        assert filtered_total < unfiltered_total

    def test_quarterly_reports_by_category(self, client):
        """Test filtering quarterly reports by category."""
        unfiltered = client.get("/api/reports/quarterly").json()
        filtered = client.get("/api/reports/quarterly?category=actuators").json()

        assert sum(q["total_orders"] for q in filtered) < sum(
            q["total_orders"] for q in unfiltered
        )

    def test_quarterly_reports_by_status(self, client):
        """Test that filtering to Delivered gives a 100% fulfillment rate."""
        response = client.get("/api/reports/quarterly?status=Delivered")
        assert response.status_code == 200

        data = response.json()
        assert len(data) > 0

        for quarter in data:
            assert quarter["delivered_orders"] == quarter["total_orders"]
            assert quarter["fulfillment_rate"] == 100.0

    def test_quarterly_reports_by_month_collapses_to_one_quarter(self, client):
        """Test that a single-month filter leaves only that month's quarter."""
        response = client.get("/api/reports/quarterly?month=2025-03")
        assert response.status_code == 200

        data = response.json()
        assert len(data) == 1
        assert data[0]["quarter"] == "Q1-2025"

    def test_quarterly_reports_by_quarter_filter(self, client):
        """Test that a quarter filter leaves only that quarter."""
        response = client.get("/api/reports/quarterly?month=Q3-2025")
        assert response.status_code == 200

        data = response.json()
        assert len(data) == 1
        assert data[0]["quarter"] == "Q3-2025"

    def test_quarterly_reports_multiple_filters(self, client):
        """Test combining warehouse, status and month filters."""
        response = client.get(
            "/api/reports/quarterly?warehouse=Tokyo&status=Delivered&month=Q1-2025"
        )
        assert response.status_code == 200

        data = response.json()
        for quarter in data:
            assert quarter["quarter"] == "Q1-2025"
            assert quarter["fulfillment_rate"] == 100.0

    def test_quarterly_reports_all_sentinel_means_no_filter(self, client):
        """Test that 'all' is treated the same as omitting the parameter."""
        unfiltered = client.get("/api/reports/quarterly").json()
        with_all = client.get(
            "/api/reports/quarterly?warehouse=all&category=all&status=all&month=all"
        ).json()

        assert with_all == unfiltered

    def test_quarterly_reports_no_matches_returns_empty_list(self, client):
        """Test that a filter matching nothing returns an empty list, not an error."""
        response = client.get("/api/reports/quarterly?warehouse=Atlantis")
        assert response.status_code == 200
        assert response.json() == []

    def test_quarterly_matches_orders_endpoint(self, client):
        """Test quarterly totals agree with the orders endpoint for the same filter."""
        orders = client.get("/api/orders?warehouse=London").json()
        quarterly = client.get("/api/reports/quarterly?warehouse=London").json()

        assert sum(q["total_orders"] for q in quarterly) == len(orders)


class TestMonthlyTrendsEndpoint:
    """Test suite for /api/reports/monthly-trends."""

    def test_get_monthly_trends(self, client):
        """Test getting monthly trends without filters."""
        response = client.get("/api/reports/monthly-trends")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

        first = data[0]
        assert "month" in first
        assert "order_count" in first
        assert "revenue" in first
        assert "delivered_count" in first

    def test_monthly_trends_sorted_by_month(self, client):
        """Test that months come back in chronological order."""
        response = client.get("/api/reports/monthly-trends")
        data = response.json()

        months = [m["month"] for m in data]
        assert months == sorted(months)

    def test_monthly_trends_month_format(self, client):
        """Test that month keys are in YYYY-MM format."""
        response = client.get("/api/reports/monthly-trends")
        data = response.json()

        for entry in data:
            assert len(entry["month"]) == 7
            year, month = entry["month"].split("-")
            assert len(year) == 4
            assert 1 <= int(month) <= 12

    def test_monthly_trends_field_types(self, client):
        """Test that monthly trend fields have proper numeric types."""
        response = client.get("/api/reports/monthly-trends")
        data = response.json()

        for entry in data:
            assert isinstance(entry["order_count"], int)
            assert isinstance(entry["revenue"], (int, float))
            assert isinstance(entry["delivered_count"], int)
            assert entry["order_count"] > 0
            assert entry["revenue"] >= 0
            assert entry["delivered_count"] <= entry["order_count"]

    def test_monthly_trends_by_warehouse(self, client):
        """Test filtering monthly trends by warehouse."""
        unfiltered = client.get("/api/reports/monthly-trends").json()
        filtered = client.get("/api/reports/monthly-trends?warehouse=Tokyo").json()

        assert sum(m["order_count"] for m in filtered) < sum(
            m["order_count"] for m in unfiltered
        )

    def test_monthly_trends_by_category(self, client):
        """Test filtering monthly trends by category."""
        response = client.get("/api/reports/monthly-trends?category=sensors")
        assert response.status_code == 200

        data = response.json()
        assert len(data) > 0

    def test_monthly_trends_by_status(self, client):
        """Test that filtering to Delivered makes every order delivered."""
        response = client.get("/api/reports/monthly-trends?status=Delivered")
        data = response.json()

        for entry in data:
            assert entry["delivered_count"] == entry["order_count"]

    def test_monthly_trends_by_month_returns_single_month(self, client):
        """Test that a single-month filter leaves exactly that month."""
        response = client.get("/api/reports/monthly-trends?month=2025-07")
        assert response.status_code == 200

        data = response.json()
        assert len(data) == 1
        assert data[0]["month"] == "2025-07"

    def test_monthly_trends_by_quarter_returns_three_months(self, client):
        """Test that a quarter filter leaves that quarter's months."""
        response = client.get("/api/reports/monthly-trends?month=Q2-2025")
        assert response.status_code == 200

        data = response.json()
        assert [m["month"] for m in data] == ["2025-04", "2025-05", "2025-06"]

    def test_monthly_trends_no_matches_returns_empty_list(self, client):
        """Test that a filter matching nothing returns an empty list."""
        response = client.get("/api/reports/monthly-trends?warehouse=Atlantis")
        assert response.status_code == 200
        assert response.json() == []

    def test_monthly_trends_matches_orders_endpoint(self, client):
        """Test monthly totals agree with the orders endpoint for the same filter."""
        orders = client.get("/api/orders?category=controllers").json()
        monthly = client.get("/api/reports/monthly-trends?category=controllers").json()

        assert sum(m["order_count"] for m in monthly) == len(orders)

    def test_monthly_revenue_sums_to_quarterly_revenue(self, client):
        """Test the two report endpoints agree on total revenue."""
        monthly = client.get("/api/reports/monthly-trends").json()
        quarterly = client.get("/api/reports/quarterly").json()

        monthly_total = sum(m["revenue"] for m in monthly)
        quarterly_total = sum(q["total_revenue"] for q in quarterly)

        assert abs(monthly_total - quarterly_total) < 0.01
