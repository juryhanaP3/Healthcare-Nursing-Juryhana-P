import json
import math
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="Career Venture Lab | NUR-2 (Precalculus)",
    page_icon="🩺",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Exact Money & Deterministic NUR-2 Simulation Engine
# ---------------------------------------------------------------------------

def to_money(val) -> Decimal:
    return Decimal(str(val)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def compute_nur_month(
    requested: int,
    base_price: Decimal,
    staff_hours: float,
    hours_per_unit: float,
    venue_seats: int,
    no_show_rate: float,
    variable_per_unit: Decimal,
    fixed_monthly: Decimal,
    ad_cost: Decimal = Decimal("0.00"),
    opening_cash: Decimal = Decimal("4000.00"),
    refund_amount: Decimal = Decimal("0.00"),
    loan_principal: Decimal = Decimal("0.00"),
    interest: Decimal = Decimal("0.00"),
    additional_capex: Decimal = Decimal("0.00"),
    new_owner_cash: Decimal = Decimal("0.00"),
    loan_cash: Decimal = Decimal("0.00"),
    capacity_override: int | None = None,
) -> dict:
    """Deterministic NUR-2 monthly operations & accounting engine."""
    staff_cap = math.floor(staff_hours / hours_per_unit) if hours_per_unit > 0 else 0
    derived_capacity = min(staff_cap, int(venue_seats))
    effective_capacity = int(capacity_override) if capacity_override is not None else derived_capacity

    booked = min(int(requested), max(0, effective_capacity))
    attended = math.floor(booked * (1.0 - float(no_show_rate)))
    sold = attended
    unserved_demand = max(0, int(requested) - booked)
    no_show_seats = max(0, booked - attended)

    gross_revenue = to_money(base_price * sold)
    net_revenue = to_money(gross_revenue - refund_amount)
    variable_expense = to_money(variable_per_unit * sold)
    fixed_expense = to_money(fixed_monthly)
    marketing_expense = to_money(ad_cost)

    total_operating_expense = to_money(variable_expense + fixed_expense + marketing_expense)
    operating_profit = to_money(net_revenue - total_operating_expense)
    net_profit = to_money(operating_profit - interest)

    ending_cash = to_money(
        opening_cash
        + net_revenue
        - variable_expense
        - fixed_expense
        - marketing_expense
        - interest
        - loan_principal
        - additional_capex
        + new_owner_cash
        + loan_cash
    )

    utilization = (booked / effective_capacity * 100.0) if effective_capacity > 0 else 0.0
    educator_hours_used = round(attended * hours_per_unit, 2)

    return {
        "requested": int(requested),
        "derived_capacity": derived_capacity,
        "effective_capacity": effective_capacity,
        "booked": booked,
        "attended": attended,
        "sold": sold,
        "no_show_seats": no_show_seats,
        "unserved_demand": unserved_demand,
        "gross_revenue": float(gross_revenue),
        "refund_amount": float(refund_amount),
        "revenue": float(net_revenue),
        "variable_expense": float(variable_expense),
        "fixed_expense": float(fixed_expense),
        "marketing_expense": float(marketing_expense),
        "total_expense": float(total_operating_expense),
        "operating_profit": float(operating_profit),
        "interest": float(interest),
        "net_profit": float(net_profit),
        "opening_cash": float(opening_cash),
        "ending_cash": float(ending_cash),
        "utilization_pct": round(utilization, 2),
        "educator_hours_used": educator_hours_used,
    }


def initial_state() -> dict:
    return {
        "team_id": "TEAM-NUR2",
        "course": "Precalculus",
        "pathway_id": "NUR-2",
        "business_name": "Nurse-Led Health Education Simulation",
        "selected_level": "Advanced",
        "snapshot_id": "SNAP-001",
        "state_version": 1,
        "simulation_date": "2027-01-31",
        "base_period": "monthly",
        "working_days": 20,
        "currency": "USD",
        "fixture_mode": False,
        # Exact NUR-2 Startup Financing & Opening Balances
        "owner_contribution": 6000.00,
        "equipment_assets": 1500.00,
        "pre_opening_expense": 500.00,
        "opening_inventory": 0.00,
        "cash": 4000.00,
        "debt": 0.00,
        "retained_earnings": -500.00,
        # Exact NUR-2 Operating & Cost Inputs
        "base_price": 25.00,
        "D0": 80,
        "staff_hours": 30.0,
        "hours_per_unit": 0.5,
        "venue_seats": 60,
        "no_show_rate": 0.0,
        "satisfaction_mean": 4.0,
        "var_costs": {
            "educator_delivery": 2.00,
            "materials": 2.00,
            "cleaning_consumables": 1.00,
        },
        "fixed_costs": {
            "venue": 250.00,
            "scheduling_software": 100.00,
            "accessibility_support": 200.00,
            "admin_insurance_assumption": 150.00,
        },
        "ledger": [],
        "executed_run_ids": [],
        "campaigns": [],
        "recommendations": [],
        "decisions": [],
    }


if "sim" not in st.session_state:
    st.session_state.sim = initial_state()

sim = st.session_state.sim

# ---------------------------------------------------------------------------
# Sidebar: Governance, Persistence, Challenge Level & Simulation Controls
# ---------------------------------------------------------------------------

with st.sidebar:
    st.title("🩺 Career Venture Lab")
    st.caption("Pathway **NUR-2** | Precalculus | Nurse-Led Health Education")

    sim["team_id"] = st.text_input("Team ID", value=sim["team_id"])
    sim["snapshot_id"] = st.text_input("Snapshot ID", value=sim["snapshot_id"])
    sim["simulation_date"] = st.text_input("Simulation Date", value=sim["simulation_date"])
    st.metric("State Version", f"v{sim['state_version']}")

    sim["selected_level"] = st.selectbox(
        "Teacher-Approved Challenge Level",
        ["Foundation", "Applied", "Advanced"],
        index=["Foundation", "Applied", "Advanced"].index(sim["selected_level"]),
    )

    sim["fixture_mode"] = st.toggle(
        "Fixture-Test Mode (capacity_override)",
        value=sim["fixture_mode"],
        help="Normal mode derives capacity from staff_hours and venue_seats. Fixture mode replays monthly_fixture.csv.",
    )
    if sim["fixture_mode"]:
        st.warning("Fixture-Test Mode active: capacity is overridden only for fixture replay.")

    st.divider()
    st.subheader("Durable Save / Load JSON")
    snapshot_json = json.dumps(sim, indent=2)
    st.download_button(
        "Export Snapshot JSON",
        data=snapshot_json,
        file_name=f"{sim['team_id']}_NUR2_v{sim['state_version']}.json",
        mime="application/json",
        use_container_width=True,
    )

    uploaded_snap = st.file_uploader("Restore Snapshot JSON", type=["json"])
    if uploaded_snap is not None:
        try:
            loaded = json.load(uploaded_snap)
            if loaded.get("pathway_id") != "NUR-2":
                st.error(f"Rejected: Expected pathway NUR-2, got {loaded.get('pathway_id')}.")
            elif loaded.get("team_id") != sim["team_id"]:
                st.error(f"Rejected: Team ID mismatch ({loaded.get('team_id')} != {sim['team_id']}).")
            else:
                st.session_state.sim = loaded
                st.success(f"Restored snapshot {loaded.get('snapshot_id')} (v{loaded.get('state_version')}).")
                st.rerun()
        except Exception as exc:
            st.error(f"Invalid JSON snapshot: {exc}")

    if st.button("Reset to Opening State ($4,000 Cash)", use_container_width=True):
        tid = sim["team_id"]
        lvl = sim["selected_level"]
        st.session_state.sim = initial_state()
        st.session_state.sim["team_id"] = tid
        st.session_state.sim["selected_level"] = lvl
        st.rerun()

# ---------------------------------------------------------------------------
# Header & Compliance Banner
# ---------------------------------------------------------------------------

st.header("Nurse-Led Health Education Simulation (NUR-2)")
st.info(
    "**Educational Simulation Notice**: All workshops, learners, transactions, and funds are fictional. "
    "This venture models nonclinical general health education only—never medical diagnosis, clinical care, or real patient data."
)

var_per_unit = to_money(sum(sim["var_costs"].values()))
fixed_per_month = to_money(sum(sim["fixed_costs"].values()))
staff_cap = math.floor(sim["staff_hours"] / sim["hours_per_unit"]) if sim["hours_per_unit"] > 0 else 0
derived_cap = min(staff_cap, int(sim["venue_seats"]))

# Top KPI Summary
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Spendable Cash", f"${sim['cash']:,.2f}", delta="Alert < $800" if sim["cash"] < 800 else "Reserve Healthy")
k2.metric("Workshop Seat Price (p₀)", f"${sim['base_price']:,.2f}")
k3.metric("Derived Monthly Capacity", f"{derived_cap} seats", delta=f"Staff: {staff_cap} | Venue: {sim['venue_seats']}")
k4.metric("Variable / Fixed Cost", f"${float(var_per_unit):.2f}/seat", delta=f"${float(fixed_per_month):.2f}/mo fixed")
k5.metric("Retained Earnings", f"${sim['retained_earnings']:,.2f}")

tabs = st.tabs([
    "1. Inputs & Operations",
    "2. Precalculus Math Panel",
    "3. Report Center & Ledger",
    "4. Marketing Studio",
    "5. AI Departmental Roles",
    "6. Cross-Course & Assessment",
    "7. Acceptance Tests",
])

# ---------------------------------------------------------------------------
# TAB 1: Inputs & Operations
# ---------------------------------------------------------------------------
with tabs[0]:
    col_in, col_ops = st.columns([1.1, 1.2])
    with col_in:
        st.subheader("Editable Operating & Cost Inputs")
        sim["base_price"] = st.number_input("Workshop Seat Price p₀ ($)", min_value=1.0, value=float(sim["base_price"]), step=1.0)
        sim["D0"] = st.number_input("Baseline Requested Demand D₀ (seats/mo)", min_value=0, value=int(sim["D0"]), step=5)
        sim["staff_hours"] = st.slider("Educator Staff Hours / Month", 0.0, 120.0, float(sim["staff_hours"]), 1.0)
        sim["hours_per_unit"] = st.number_input("Productive Hours / Seat", min_value=0.1, value=float(sim["hours_per_unit"]), step=0.1)
        sim["venue_seats"] = st.slider("Venue Seats / Month", 0, 150, int(sim["venue_seats"]), 5)
        sim["no_show_rate"] = st.slider("No-Show Rate (0.00 to 1.00)", 0.0, 1.0, float(sim["no_show_rate"]), 0.05)

        st.markdown("**Per-Attended-Seat Variable Costs ($/unit)**")
        vc1, vc2, vc3 = st.columns(3)
        sim["var_costs"]["educator_delivery"] = vc1.number_input("Educator Delivery ($)", 0.0, 50.0, float(sim["var_costs"]["educator_delivery"]), 0.5)
        sim["var_costs"]["materials"] = vc2.number_input("Materials ($)", 0.0, 50.0, float(sim["var_costs"]["materials"]), 0.5)
        sim["var_costs"]["cleaning_consumables"] = vc3.number_input("Cleaning ($)", 0.0, 50.0, float(sim["var_costs"]["cleaning_consumables"]), 0.5)

        st.markdown("**Monthly Fixed Operating Costs ($/month)**")
        fc1, fc2 = st.columns(2)
        sim["fixed_costs"]["venue"] = fc1.number_input("Venue ($)", 0.0, 2000.0, float(sim["fixed_costs"]["venue"]), 25.0)
        sim["fixed_costs"]["scheduling_software"] = fc2.number_input("Scheduling Software ($)", 0.0, 2000.0, float(sim["fixed_costs"]["scheduling_software"]), 25.0)
        sim["fixed_costs"]["accessibility_support"] = fc1.number_input("Accessibility Support ($)", 0.0, 2000.0, float(sim["fixed_costs"]["accessibility_support"]), 25.0)
        sim["fixed_costs"]["admin_insurance_assumption"] = fc2.number_input("Admin & Insurance ($)", 0.0, 2000.0, float(sim["fixed_costs"]["admin_insurance_assumption"]), 25.0)

    with col_ops:
        st.subheader("Single-Period Preview & Approved Ledger Step")
        preview_req = st.number_input("Requested Seats for Next Run", min_value=0, value=int(sim["D0"]), step=1)
        preview_ad = st.number_input("Approved Own-Marketing Expense ($)", min_value=0.0, value=0.0, step=25.0)

        var_per_unit = to_money(sum(sim["var_costs"].values()))
        fixed_per_month = to_money(sum(sim["fixed_costs"].values()))

        res = compute_nur_month(
            requested=preview_req,
            base_price=to_money(sim["base_price"]),
            staff_hours=sim["staff_hours"],
            hours_per_unit=sim["hours_per_unit"],
            venue_seats=sim["venue_seats"],
            no_show_rate=sim["no_show_rate"],
            variable_per_unit=var_per_unit,
            fixed_monthly=fixed_per_month,
            ad_cost=to_money(preview_ad),
            opening_cash=to_money(sim["cash"]),
        )

        st.markdown(
            f"- **Capacity Bottleneck**: `min(floor({sim['staff_hours']}/{sim['hours_per_unit']})={staff_cap}, venue={sim['venue_seats']})` = **{res['effective_capacity']} seats**
"
            f"- **Flow**: Requested `{res['requested']}` → Booked `{res['booked']}` → Attended/Sold `{res['sold']}` (Unserved: `{res['unserved_demand']}`, No-shows: `{res['no_show_seats']}`)
"
            f"- **Projected Revenue**: `${res['revenue']:,.2f}` | **Total Expense**: `${res['total_expense']:,.2f}` | **Operating Profit**: `${res['operating_profit']:,.2f}`
"
            f"- **Projected Closing Cash**: `${res['ending_cash']:,.2f}`"
        )

        run_id_input = st.text_input("Unique Run ID (Duplicate Protection)", value=f"RUN-{sim['state_version']:03d}")
        if st.button("Approve & Advance Simulation One Month", type="primary"):
            if run_id_input in sim["executed_run_ids"]:
                st.error(f"Duplicate Run Rejected: `{run_id_input}` has already been committed to the ledger.")
            else:
                sim["executed_run_ids"].append(run_id_input)
                sim["cash"] = res["ending_cash"]
                sim["retained_earnings"] = round(sim["retained_earnings"] + res["net_profit"], 2)
                sim["state_version"] += 1
                entry = {
                    "run_id": run_id_input,
                    "state_version": sim["state_version"],
                    "date": sim["simulation_date"],
                    "status": "ACTUAL",
                    **res,
                }
                sim["ledger"].append(entry)
                st.success(f"Committed `{run_id_input}` → Advanced to state v{sim['state_version']}.")
                st.rerun()

# ---------------------------------------------------------------------------
# TAB 2: Precalculus Math Panel (Foundation / Applied / Advanced)
# ---------------------------------------------------------------------------
with tabs[1]:
    st.subheader(f"Precalculus Math Skills Panel — {sim['selected_level']} Mode")
    p0 = float(sim["base_price"])
    D0 = float(sim["D0"])
    v = float(var_per_unit)
    F = float(fixed_per_month)
    cap = derived_cap

    if sim["selected_level"] == "Foundation":
        st.markdown(
            f"**Concept**: Rational Average Cost Function $A(s) = \frac{{F}}{{s}} + v = \frac{{{F:.0f}}}{{s}} + {v:.2f}$ on domain $0 < s \le {cap}$.
"
            f"- **Vertical Asymptote**: $s = 0$ ($A(0)$ is undefined; fixed cost cannot be spread over zero seats).
"
            f"- **Horizontal Behavior**: As $s \to \infty$, $A(s) \to {v:.2f}$ (unit variable cost), though practical domain stops at capacity $s = {cap}$ where $A({cap}) = \${(F/cap + v):.2f}/\text{{seat}}$."
        )
        s_vals = np.linspace(1, max(1, cap), 100)
        a_vals = F / s_vals + v
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=s_vals, y=a_vals, mode="lines", name="A(s) = F/s + v"))
        fig.add_hline(y=v, line_dash="dash", annotation_text=f"Horizontal Asymptote y = ${v:.2f}")
        fig.update_layout(title="Average Cost per Attended Seat A(s)", xaxis_title="Attended Seats (s)", yaxis_title="Average Cost ($/seat)")
        st.plotly_chart(fig, use_container_width=True)

        df_f = pd.DataFrame({
            "Seats (s)": [0, 10, 20, 30, 45, cap],
            "Total Cost C(s) ($)": [F + v * s for s in [0, 10, 20, 30, 45, cap]],
            "Average Cost A(s) ($/seat)": ["UNDEFINED (VA)" if s == 0 else round(F / s + v, 2) for s in [0, 10, 20, 30, 45, cap]],
        })
        st.dataframe(df_f, use_container_width=True)

    elif sim["selected_level"] == "Applied":
        slope = D0 / p0
        breakpoint_p = p0 * (2.0 - cap / D0) if D0 > 0 else 0.0
        st.markdown(
            f"**Concept**: Function Composition with Capacity Constraint
"
            f"- Demand: $q(p) = \max(0,\, {2*D0:.1f} - {slope:.2f}p)$ on $0 \le p \le {2*p0:.2f}$
"
            f"- Realized Sales: $s(p) = \min({cap},\, q(p))$
"
            f"- Composed Revenue $R(p) = p \cdot s(p)$, Cost $C(s(p)) = {F:.0f} + {v:.2f}s(p)$, Profit $P(p) = R(p) - C(s(p))$
"
            f"- **Capacity Breakpoint**: $p = p_0(2 - \text{{cap}}/D_0) = \${breakpoint_p:.2f}$ (below this price, sales are capped at {cap} seats)."
        )
        p_vals = np.linspace(0, 2 * p0, 200)
        q_vals = np.maximum(0.0, 2 * D0 - slope * p_vals)
        s_vals = np.minimum(cap, q_vals)
        r_vals = p_vals * s_vals
        c_vals = F + v * s_vals
        prof_vals = r_vals - c_vals

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=p_vals, y=r_vals, name="Composed Revenue R(p)"))
        fig.add_trace(go.Scatter(x=p_vals, y=c_vals, name="Composed Cost C(s(p))"))
        fig.add_trace(go.Scatter(x=p_vals, y=prof_vals, name="Composed Profit P(p)", line=dict(width=3)))
        fig.add_hline(y=0, line_dash="dot")
        fig.add_vline(x=breakpoint_p, line_dash="dash", annotation_text=f"Capacity Breakpoint p=${breakpoint_p:.2f}")
        fig.update_layout(title="Composed Revenue, Cost & Profit vs. Seat Price (Continuous View)", xaxis_title="Price p ($)", yaxis_title="USD ($)")
        st.plotly_chart(fig, use_container_width=True)

    else:  # Advanced
        st.markdown(
            "**Concept**: Seasonal Trigonometric Demand Model (Unlocked after Trigonometry)
"
            f"- $D(t) = D_0\left(1 + 0.20\sin\left(\frac{{2\pi(t - 1)}}{{12}}\right)\right)$ for month $t \in [1, 12]$, period $12$ months.
"
            f"- Peak unconstrained demand occurs at $t = 4$ ($1.20 D_0 = {1.2*D0:.1f}$ seats); trough occurs at $t = 10$ ($0.80 D_0 = {0.8*D0:.1f}$ seats).
"
            "- **Extrapolation & Capacity Warning**: Seasonal multipliers are fictional teaching assumptions; realized sales are clipped at capacity."
        )
        t_vals = np.arange(1, 13)
        d_unconstrained = D0 * (1.0 + 0.20 * np.sin(2 * np.pi * (t_vals - 1) / 12.0))
        s_clipped = np.minimum(cap, np.floor(d_unconstrained))
        unserved = np.maximum(0, np.floor(d_unconstrained) - s_clipped)

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=t_vals, y=d_unconstrained, mode="lines+markers", name="Seasonal Demand D(t)"))
        fig.add_trace(go.Bar(x=t_vals, y=s_clipped, name="Realized Sales (Clipped at Capacity)", opacity=0.7))
        fig.add_hline(y=cap, line_dash="dash", annotation_text=f"Capacity Cap ({cap} seats)")
        fig.update_layout(title="12-Month Seasonal Demand D(t) vs. Capacity-Clipped Sales", xaxis_title="Month Index (t)", yaxis_title="Workshop Seats")
        st.plotly_chart(fig, use_container_width=True)

        df_adv = pd.DataFrame({
            "Month (t)": t_vals,
            "Unconstrained D(t)": np.round(d_unconstrained, 2),
            "Capacity Cap": cap,
            "Realized Sales (Integer)": s_clipped.astype(int),
            "Unserved Demand": unserved.astype(int),
        })
        st.dataframe(df_adv, use_container_width=True)

    st.divider()
    st.markdown("**Transfer Check (Predict Before Calculating)**")
    user_pred = st.text_input("Explain the difference between total cost C(60) and average cost A(60) with units, and why q=0 is excluded:")
    if user_pred:
        st.caption(f"Reference Check: C(60) = ${F + v*60:.2f} total dollars for 60 seats; A(60) = ${(F + v*60)/60:.2f} per seat. At s=0, division by zero is undefined.")

# ---------------------------------------------------------------------------
# TAB 3: Report Center & Ledger
# ---------------------------------------------------------------------------
with tabs[2]:
    st.subheader("Reconciled Report Center & Dated Event Ledger")
    st.caption(f"Team: {sim['team_id']} | Pathway: NUR-2 | Snapshot: {sim['snapshot_id']} (v{sim['state_version']}) | Viewing reports does not create transactions.")

    r1, r2 = st.columns(2)
    with r1:
        st.markdown("#### Simplified Balance Sheet (Current State)")
        total_assets = round(sim["cash"] + sim["equipment_assets"] + sim["opening_inventory"], 2)
        total_liab_eq = round(sim["debt"] + sim["owner_contribution"] + sim["retained_earnings"], 2)
        bs_df = pd.DataFrame([
            {"Category": "Asset", "Account": "Spendable Cash", "Amount ($)": sim["cash"]},
            {"Category": "Asset", "Account": "Equipment Assets (Gross)", "Amount ($)": sim["equipment_assets"]},
            {"Category": "Asset", "Account": "Inventory", "Amount ($)": sim["opening_inventory"]},
            {"Category": "TOTAL ASSETS", "Account": "Assets = Liabilities + Equity", "Amount ($)": total_assets},
            {"Category": "Liability", "Account": "Simulated Loan Debt", "Amount ($)": sim["debt"]},
            {"Category": "Equity", "Account": "Owner Contribution", "Amount ($)": sim["owner_contribution"]},
            {"Category": "Equity", "Account": "Retained Earnings (incl. -$500 pre-opening)", "Amount ($)": sim["retained_earnings"]},
            {"Category": "TOTAL L + E", "Account": "Reconciled Total", "Amount ($)": total_liab_eq},
        ])
        st.dataframe(bs_df, use_container_width=True, hide_index=True)

    with r2:
        st.markdown("#### Scenario Forecast (1.00 / 1.10 / 0.90 Multipliers)")
        scen_rows = []
        for label, mult in [("Downside (0.90x)", 0.90), ("Baseline (1.00x)", 1.00), ("Upside (1.10x)", 1.10)]:
            req_s = math.floor(sim["D0"] * mult)
            out = compute_nur_month(
                requested=req_s,
                base_price=to_money(sim["base_price"]),
                staff_hours=sim["staff_hours"],
                hours_per_unit=sim["hours_per_unit"],
                venue_seats=sim["venue_seats"],
                no_show_rate=sim["no_show_rate"],
                variable_per_unit=var_per_unit,
                fixed_monthly=fixed_per_month,
                opening_cash=to_money(sim["cash"]),
            )
            scen_rows.append({
                "Scenario (PROJECTED)": label,
                "Requested": out["requested"],
                "Sold": out["sold"],
                "Revenue ($)": out["revenue"],
                "Expense ($)": out["total_expense"],
                "Profit ($)": out["operating_profit"],
                "Closing Cash ($)": out["ending_cash"],
            })
        st.dataframe(pd.DataFrame(scen_rows), use_container_width=True, hide_index=True)

    st.markdown("#### Committed Event Ledger (ACTUAL)")
    if sim["ledger"]:
        ledger_df = pd.DataFrame(sim["ledger"])
        st.dataframe(ledger_df, use_container_width=True)
        st.download_button(
            "Export Ledger CSV",
            data=ledger_df.to_csv(index=False),
            file_name=f"{sim['team_id']}_NUR2_ledger.csv",
            mime="text/csv",
        )
    else:
        st.info("No actual monthly runs committed yet. Approve a run in Tab 1 or run the fixture test in Tab 7.")

# ---------------------------------------------------------------------------
# TAB 4: Costed Marketing Studio
# ---------------------------------------------------------------------------
with tabs[3]:
    st.subheader("Costed Marketing Studio (Approval-Gated)")
    m1, m2 = st.columns(2)
    with m1:
        camp_id = st.text_input("Campaign ID", value=f"CAMP-{len(sim['campaigns'])+1:03d}")
        offering = st.selectbox("Workshop Offering", [
            "General wellness education workshop",
            "Caregiver information session",
            "First-aid awareness demonstration",
        ])
        audience = st.text_input("Target Fictional Audience", value="Community caregivers & local families")
        claim = st.text_input("Approved Educational Claim", value="Practical home safety and wellness literacy—educational only.")
        design_hrs = st.number_input("Design Labor Hours", 0.0, 40.0, 2.0, 0.5)
        design_rate = st.number_input("Design Rate ($/hr)", 0.0, 100.0, 20.0, 5.0)
        assets_cost = st.number_input("Licensed Assets ($)", 0.0, 500.0, 10.0, 5.0)
        print_qty = st.number_input("Print Quantity", 0, 1000, 50, 10)
        print_unit = st.number_input("Print Unit Cost ($)", 0.0, 10.0, 0.50, 0.10)
        dist_place = st.number_input("Distribution & Placement ($)", 0.0, 500.0, 25.0, 5.0)

        total_camp_cost = round(design_hrs * design_rate + assets_cost + print_qty * print_unit + dist_place, 2)
        st.metric("Total Itemized Campaign Cost", f"${total_camp_cost:,.2f}")

    with m2:
        st.markdown("#### Draft Flyer Preview (No Auto-Publishing)")
        st.code(
            f"[{offering.upper()}]
"
            f"Audience: {audience}
"
            f"Key Message: {claim}
"
            f"Seat Fee: ${sim['base_price']:.2f} | Contact: workshops@fictional-nur2.edu
"
            f"Notice: Educational simulation only; not medical advice.",
            language="text",
        )
        conversions = st.number_input("Simulated Attributed Conversions (seats)", 0, 100, 0, 1)
        cac_display = f"${total_camp_cost / conversions:.2f}" if conversions > 0 else "N/A (0 conversions)"
        st.write(f"**Customer Acquisition Cost (CAC)**: `{cac_display}`")

        if st.button("Approve & Log Campaign Expense Once"):
            if any(c["campaign_id"] == camp_id for c in sim["campaigns"]):
                st.error(f"Duplicate Campaign Rejected: `{camp_id}` already recorded.")
            else:
                sim["cash"] = round(sim["cash"] - total_camp_cost, 2)
                sim["retained_earnings"] = round(sim["retained_earnings"] - total_camp_cost, 2)
                sim["state_version"] += 1
                sim["campaigns"].append({
                    "campaign_id": camp_id,
                    "offering": offering,
                    "total_cost": total_camp_cost,
                    "conversions": conversions,
                    "cac": cac_display,
                    "state_version": sim["state_version"],
                })
                st.success(f"Logged `{camp_id}` (${total_camp_cost:.2f}) once.")
                st.rerun()

# ---------------------------------------------------------------------------
# TAB 5: AI Departmental Roles (Copy-Ready Prompts)
# ---------------------------------------------------------------------------
with tabs[4]:
    st.subheader("Copy-Ready AI Departmental Assistant Prompts (NUR-2)")
    role_choice = st.selectbox("Select Departmental Assistant", [
        "Finance Analyst",
        "Operations Planner",
        "Market and Marketing Specialist",
        "Independent Reviewer",
    ])

    common_block = (
        "You support Career Venture Lab, a fictional student business simulation. Read the selected "
        "course-career card (NUR-2, Precalculus), business brief, data dictionary and current snapshot. "
        "Identify team_id, course, pathway_id, snapshot_id, state_version, simulation date and period. "
        "If critical inputs are missing, ask for them; do not invent evidence. Use only this version; "
        "reject mismatched or stale records. Label supplied, researched, estimated and simulated values. "
        "Distinguish demand from completed sales, profit from cash, revenue from financing, and principal from interest. "
        "Do not commit changes, advance time, launch ads, send messages, or publish. Return: role; snapshot/version; "
        "question; evidence; method/calculation; recommendation; two alternatives; uncertainty; cross-department effects; "
        "proposed_changes; checks_needed; approval_status=pending. Ask the student to independently verify one step. "
        "Do not provide clinical diagnosis or personal medical advice."
    )

    dept_blocks = {
        "Finance Analyst": (
            "You are the Nurse-led health education simulation finance analyst. Use NUR cost rows ($5/attended seat variable, "
            "$700/mo fixed) and accounting rules. Reconcile revenue, variable expense, fixed expense, marketing, cash and equity. "
            "Separate startup assets ($1,500) and pre-opening expenses ($500) from current-period costs. Compare a price change "
            "and a capacity change using the Precalculus adapter. Flag cash below $800. Return calculation, report IDs, alternatives "
            "and proposed_changes only."
        ),
        "Operations Planner": (
            "You are the Nurse-led health education simulation operations planner. Apply exact NUR algorithm: "
            "booked=min(requested, floor(staff_hours/hours_per_unit), venue_seats); attended=floor(booked*(1-no_show_rate)); sold=attended. "
            "Collect payment and incur per-seat expenses only for attended seats. Identify bottleneck and lost demand. Compare one "
            "extra-resource scenario with a lower-demand scenario."
        ),
        "Market and Marketing Specialist": (
            "You are the Nurse-led health education simulation market/marketing specialist. Offerings: General wellness education workshop; "
            "caregiver information session; first-aid awareness demonstration. Draft a flyer or ad with itemized cost; success means "
            "invited learner attending a fictional workshop. No automatic demand lift. Compare two variants and propose a measurable "
            "experiment. Return draft and pending campaign_id; never launch."
        ),
        "Independent Reviewer": (
            "You review the Nurse-led health education simulation system. Verify the current snapshot and independently recompute one report, "
            "one capacity result, and the no-show test (no_show_rate=0.20 -> booked=60, attended=48, revenue=$1,200, profit=$260). "
            "Do not infer health outcomes from attendance/satisfaction. Extra accessibility spending must be an explicit line item. "
            "Model fictional general education, never diagnosis or clinical care."
        ),
    }

    full_prompt = f"{common_block}

--- DEPARTMENT ROLE ---
{dept_blocks[role_choice]}

--- CURRENT SNAPSHOT ---
{json.dumps(sim, indent=2)}"
    st.text_area("Copy into Gemini Gem / Skill / ChatGPT Role", value=full_prompt, height=320)

# ---------------------------------------------------------------------------
# TAB 6: Cross-Course & Snapshot Assessment
# ---------------------------------------------------------------------------
with tabs[5]:
    st.subheader("Cross-Course Connections & Snapshot-Based Practice Assessment")
    st.markdown(
        "**Required Cross-Course Evidence (NUR-2)**:
"
        "1. **Healthcare / CTE**: Evaluate an official public health-education source (e.g., CDC/NIH community education guidelines) and document nonclinical scope.
"
        "2. **English / Media**: Revise a fictional workshop flyer for plain-language clarity and accessibility compliance."
    )
    st.divider()
    st.markdown(f"**Frozen Snapshot Practice Check (`{sim['snapshot_id']}` | v{sim['state_version']})**")
    st.write(f"1. **Precalculus Rational Function**: Given $F = \${float(fixed_per_month):.2f}$ and $v = \${float(var_per_unit):.2f}$, compute $A(60)$ and explain why $A(0)$ is undefined.")
    st.write(f"2. **Composition & Capacity**: Using $q(p) = 160 - 3.2p$ and capacity $60$, find the price breakpoint where demand equals capacity.")
    if st.checkbox("Reveal Practice Answer Key"):
        st.success(
            f"- **Item 1**: $A(60) = {float(fixed_per_month):.2f}/60 + {float(var_per_unit):.2f} = \${float(fixed_per_month)/60 + float(var_per_unit):.2f}/\text{{seat}}$. $A(0)$ divides by zero.
"
            "- **Item 2**: $160 - 3.2p = 60 \implies 3.2p = 100 \implies p = \$31.25$."
        )

# ---------------------------------------------------------------------------
# TAB 7: Acceptance Tests (NUR-2 Fixture & Handbook Checks)
# ---------------------------------------------------------------------------
with tabs[6]:
    st.subheader("Automated Acceptance Test Suite (NUR-2 Package)")
    if st.button("Execute All NUR-2 Acceptance Tests", type="primary"):
        results = []

        # 1. 3-Month Fixture Replay
        cash = Decimal("4000.00")
        fixture_rows = [
            ("2027-01", 80, 60, Decimal("0.00"), 60, 1500.00, 1000.00, 500.00, 4500.00),
            ("2027-02", 88, 60, Decimal("100.00"), 60, 1500.00, 1100.00, 400.00, 4900.00),
            ("2027-03", 72, 45, Decimal("0.00"), 45, 1125.00, 925.00, 200.00, 5100.00),
        ]
        for m, req, cap_ov, ad, exp_s, exp_r, exp_e, exp_p, exp_c in fixture_rows:
            out = compute_nur_month(
                requested=req,
                base_price=Decimal("25.00"),
                staff_hours=30.0,
                hours_per_unit=0.5,
                venue_seats=60,
                no_show_rate=0.0,
                variable_per_unit=Decimal("5.00"),
                fixed_monthly=Decimal("700.00"),
                ad_cost=ad,
                opening_cash=cash,
                capacity_override=cap_ov,
            )
            cash = Decimal(str(out["ending_cash"]))
            passed = (
                out["sold"] == exp_s
                and abs(out["revenue"] - exp_r) < 0.01
                and abs(out["total_expense"] - exp_e) < 0.01
                and abs(out["operating_profit"] - exp_p) < 0.01
                and abs(out["ending_cash"] - exp_c) < 0.01
            )
            results.append({"Test": f"Fixture {m}", "Expected": f"Sold={exp_s}, Cash=${exp_c:.0f}", "Actual": f"Sold={out['sold']}, Cash=${out['ending_cash']:.0f}", "Status": "PASS" if passed else "FAIL"})

        # 2. Business-Specific Test: no_show_rate = 0.20
        ns = compute_nur_month(80, Decimal("25.00"), 30.0, 0.5, 60, 0.20, Decimal("5.00"), Decimal("700.00"))
        ns_pass = (ns["booked"] == 60 and ns["attended"] == 48 and ns["revenue"] == 1200.0 and ns["variable_expense"] == 240.0 and ns["operating_profit"] == 260.0)
        results.append({"Test": "No-Show 20% Rule", "Expected": "Booked=60, Att=48, Rev=$1200, Prof=$260", "Actual": f"Booked={ns['booked']}, Att={ns['attended']}, Rev=${ns['revenue']:.0f}, Prof=${ns['operating_profit']:.0f}", "Status": "PASS" if ns_pass else "FAIL"})

        # 3. Zero-Sales Boundary
        zs = compute_nur_month(0, Decimal("25.00"), 30.0, 0.5, 60, 0.0, Decimal("5.00"), Decimal("700.00"))
        zs_pass = (zs["revenue"] == 0.0 and zs["variable_expense"] == 0.0 and zs["operating_profit"] == -700.0)
        results.append({"Test": "Zero Sales Boundary", "Expected": "Rev=$0, Var=$0, Prof=-$700", "Actual": f"Rev=${zs['revenue']:.0f}, Var=${zs['variable_expense']:.0f}, Prof=${zs['operating_profit']:.0f}", "Status": "PASS" if zs_pass else "FAIL"})

        # 4. Precalculus Acceptance Checks
        a_cap = 700.0 / 60.0 + 5.0
        d_m4 = 80.0 * (1.0 + 0.20 * math.sin(2 * math.pi * (4 - 1) / 12.0))
        d_m10 = 80.0 * (1.0 + 0.20 * math.sin(2 * math.pi * (10 - 1) / 12.0))
        pc_pass = abs(a_cap - 16.6667) < 0.01 and abs(d_m4 - 96.0) < 0.01 and abs(d_m10 - 64.0) < 0.01
        results.append({"Test": "Precalculus Adapter Checks", "Expected": "A(60)=$16.67, D(4)=96, D(10)=64", "Actual": f"A(60)=${a_cap:.2f}, D(4)={d_m4:.1f}, D(10)={d_m10:.1f}", "Status": "PASS" if pc_pass else "FAIL"})

        st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)
