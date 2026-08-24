"""
Tests for the inventory coverage endpoint (days of cover vs supplier lead time).
"""
import pytest


VALID_RISKS = {"stockout", "critical", "warning", "ok", "idle"}
AT_RISK = {"stockout", "critical"}


class TestInventoryCoverageEndpoint:
    """Test suite for /api/inventory/coverage."""

    def test_route_is_not_shadowed_by_item_id(self, client):
        """Test /coverage resolves as its own route, not as item_id="coverage".

        Starlette matches in registration order, so if this route were declared
        after /api/inventory/{item_id} the path param would capture "coverage"
        and return 404.
        """
        response = client.get("/api/inventory/coverage")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

        # The sibling routes must still behave.
        assert client.get("/api/inventory/1").status_code == 200
        assert client.get("/api/inventory/definitely-not-an-item").status_code == 404

    def test_get_coverage_structure(self, client):
        """Test the coverage payload carries every inventory and metric field."""
        response = client.get("/api/inventory/coverage")
        assert response.status_code == 200

        data = response.json()
        assert len(data) > 0

        row = data[0]
        for field in (
            "sku", "name", "category", "warehouse", "location",
            "quantity_on_hand", "reorder_point", "unit_cost",
            "forecasted_demand", "demand_source", "daily_demand",
            "days_of_cover", "lead_time_days", "risk",
            "shortfall_at_lead_time", "below_reorder_point",
        ):
            assert field in row, field

    def test_covers_every_inventory_item(self, client):
        """Test coverage reports on all inventory, not just at-risk items."""
        inventory = client.get("/api/inventory").json()
        coverage = client.get("/api/inventory/coverage").json()

        assert len(coverage) == len(inventory)
        assert {r["sku"] for r in coverage} == {i["sku"] for i in inventory}

    def test_risk_values_are_valid(self, client):
        """Test every row carries a known risk level."""
        data = client.get("/api/inventory/coverage").json()
        for row in data:
            assert row["risk"] in VALID_RISKS

    def test_field_types(self, client):
        """Test numeric fields have proper types and sane ranges."""
        data = client.get("/api/inventory/coverage").json()
        for row in data:
            assert isinstance(row["daily_demand"], (int, float))
            assert isinstance(row["lead_time_days"], int)
            assert isinstance(row["shortfall_at_lead_time"], int)
            assert row["daily_demand"] >= 0
            assert row["lead_time_days"] > 0
            assert row["shortfall_at_lead_time"] >= 0
            assert row["days_of_cover"] is None or row["days_of_cover"] >= 0

    def test_days_of_cover_calculation(self, client):
        """Test days of cover equals stock on hand divided by daily demand."""
        data = client.get("/api/inventory/coverage").json()
        checked = 0
        for row in data:
            if row["daily_demand"] > 0:
                expected = row["quantity_on_hand"] / row["daily_demand"]
                assert abs(row["days_of_cover"] - expected) < 0.15
                checked += 1
        assert checked > 0

    def test_daily_demand_is_thirty_day_demand_over_thirty(self, client):
        """Test the daily rate derives from the 30-day demand figure."""
        data = client.get("/api/inventory/coverage").json()
        for row in data:
            assert abs(row["daily_demand"] - row["forecasted_demand"] / 30) < 0.01

    def test_no_demand_reports_unbounded_cover_as_idle(self, client):
        """Test a SKU with no demand signal gets null cover and idle risk."""
        data = client.get("/api/inventory/coverage").json()
        for row in data:
            if row["daily_demand"] == 0:
                assert row["days_of_cover"] is None
                assert row["risk"] == "idle"
                assert row["shortfall_at_lead_time"] == 0

    def test_critical_means_cover_below_lead_time(self, client):
        """Test the alarm condition is cover shorter than the lead time."""
        data = client.get("/api/inventory/coverage").json()
        at_risk = [r for r in data if r["risk"] in AT_RISK]
        assert len(at_risk) > 0

        for row in at_risk:
            if row["risk"] == "critical":
                assert row["days_of_cover"] < row["lead_time_days"]

    def test_ok_means_comfortable_margin_over_lead_time(self, client):
        """Test an 'ok' row has cover well clear of its lead time."""
        data = client.get("/api/inventory/coverage").json()
        for row in data:
            if row["risk"] == "ok":
                assert row["days_of_cover"] >= row["lead_time_days"] * 1.5

    def test_warning_sits_between_lead_time_and_the_margin(self, client):
        """Test 'warning' covers the band between lead time and 1.5x it."""
        data = client.get("/api/inventory/coverage").json()
        for row in data:
            if row["risk"] == "warning":
                assert row["lead_time_days"] <= row["days_of_cover"]
                assert row["days_of_cover"] < row["lead_time_days"] * 1.5

    def test_shortfall_at_lead_time_calculation(self, client):
        """Test the reorder quantity is lead-time consumption minus stock."""
        data = client.get("/api/inventory/coverage").json()
        for row in data:
            expected = max(
                0, round(row["daily_demand"] * row["lead_time_days"]) - row["quantity_on_hand"]
            )
            assert abs(row["shortfall_at_lead_time"] - expected) <= 1

    def test_sorted_worst_risk_first(self, client):
        """Test rows come back ordered by severity."""
        order = {"stockout": 0, "critical": 1, "warning": 2, "ok": 3, "idle": 4}
        data = client.get("/api/inventory/coverage").json()
        weights = [order[r["risk"]] for r in data]
        assert weights == sorted(weights)

    def test_signal_differs_from_the_reorder_point(self, client):
        """Test the metric is not just a restatement of the reorder point.

        This is the whole reason the endpoint exists: an item can be above its
        reorder point and still be unable to replenish before running dry,
        because the reorder point ignores lead time.
        """
        data = client.get("/api/inventory/coverage").json()
        at_risk_above_reorder = [
            r for r in data if r["risk"] in AT_RISK and not r["below_reorder_point"]
        ]
        assert len(at_risk_above_reorder) > 0

    def test_coverage_by_warehouse(self, client):
        """Test filtering coverage by warehouse."""
        response = client.get("/api/inventory/coverage?warehouse=Tokyo")
        assert response.status_code == 200

        data = response.json()
        assert len(data) > 0
        for row in data:
            assert row["warehouse"] == "Tokyo"

    def test_coverage_by_category(self, client):
        """Test filtering coverage by category."""
        response = client.get("/api/inventory/coverage?category=actuators")
        assert response.status_code == 200

        data = response.json()
        assert len(data) > 0
        for row in data:
            assert row["category"].lower() == "actuators"

    def test_coverage_all_sentinel_means_no_filter(self, client):
        """Test 'all' behaves the same as omitting the parameter."""
        unfiltered = client.get("/api/inventory/coverage").json()
        with_all = client.get("/api/inventory/coverage?warehouse=all&category=all").json()
        assert with_all == unfiltered

    def test_coverage_no_matches_returns_empty_list(self, client):
        """Test a filter matching nothing returns an empty list, not an error."""
        response = client.get("/api/inventory/coverage?warehouse=Atlantis")
        assert response.status_code == 200
        assert response.json() == []

    def test_lead_times_are_per_category(self, client):
        """Test lead time is consistent within a category and varies across."""
        data = client.get("/api/inventory/coverage").json()

        by_category = {}
        for row in data:
            by_category.setdefault(row["category"].lower(), set()).add(row["lead_time_days"])

        for category, lead_times in by_category.items():
            assert len(lead_times) == 1, f"{category} has inconsistent lead times"

        assert len({next(iter(v)) for v in by_category.values()}) > 1


class TestRestockingUsesCoverage:
    """The restocking recommendation now ranks on cover, not the reorder point."""

    def test_candidates_carry_coverage_fields(self, client):
        """Test recommendations expose the metrics that drive their ranking."""
        data = client.get("/api/restocking/recommendations?budget=250000").json()
        rows = data["recommended"] + data["deferred"]
        assert len(rows) > 0

        for row in rows:
            assert "daily_demand" in row
            assert "days_of_cover" in row
            assert "risk" in row
            assert row["risk"] in VALID_RISKS

    def test_critical_urgency_tracks_the_risk_level(self, client):
        """Test urgency is derived from risk rather than the reorder point."""
        data = client.get("/api/restocking/recommendations?budget=2000000").json()
        for row in data["recommended"] + data["deferred"]:
            if row["risk"] in AT_RISK:
                assert row["urgency"] == "critical"
            elif row["risk"] == "warning":
                assert row["urgency"] == "high"
            else:
                assert row["urgency"] == "moderate"

    def test_ranked_by_severity_then_least_cover(self, client):
        """Test the candidate order is worst risk first, then thinnest cover."""
        order = {"stockout": 0, "critical": 1, "warning": 2, "ok": 3, "idle": 4}
        data = client.get("/api/restocking/recommendations?budget=2000000").json()
        rows = data["recommended"] + data["deferred"]

        keys = [
            (order[r["risk"]], r["days_of_cover"] if r["days_of_cover"] is not None else float("inf"))
            for r in rows
        ]
        assert keys == sorted(keys)

    def test_coverage_and_restocking_agree_on_a_shared_sku(self, client):
        """Test both endpoints report the same cover for the same item."""
        coverage = {r["sku"]: r for r in client.get("/api/inventory/coverage").json()}
        data = client.get("/api/restocking/recommendations?budget=2000000").json()

        compared = 0
        for row in data["recommended"] + data["deferred"]:
            reference = coverage[row["sku"]]
            assert row["days_of_cover"] == reference["days_of_cover"]
            assert row["risk"] == reference["risk"]
            assert row["lead_time_days"] == reference["lead_time_days"]
            compared += 1
        assert compared > 0
