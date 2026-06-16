import serpapi
import os

client = serpapi.Client(api_key=os.environ["SERPAPI_KEY"])

RETURN_DATES = [
    "2027-01-18",
    "2027-01-19",
    "2027-01-20",
    "2027-01-21",
    "2027-01-22",
    "2027-01-23",
    "2027-01-24",
]

def format_flight_details(flight):
    """Extract detailed info from a flight option."""
    legs = flight.get("flights", [])
    price = flight.get("price", "N/A")
    total_duration = flight.get("total_duration", "N/A")

    airlines = " → ".join(leg.get("airline", "?") for leg in legs)

    layovers = flight.get("layovers", [])
    if layovers:
        layover_parts = []
        for l in layovers:
            airport = l.get("name", "?")
            code = l.get("id", "")
            duration = l.get("duration", "?")
            layover_parts.append(f"{airport} ({code}), {duration} mins")
        layover_str = " | ".join(layover_parts)
    else:
        layover_str = "Direct (no layover)"

    lines = []
    lines.append(f"   Airlines:         {airlines}")
    lines.append(f"   Total Price:      £{price}")
    lines.append(f"   Total Duration:   {total_duration} mins")
    lines.append(f"   Layover(s):       {layover_str}")
    return "\n".join(lines)

all_trips = []  # store (total_price, outbound_airline, return_airline, return_date) for summary

lines = ["✈️  LHR ⇄ HKG Flight Search (3 Adults, Christmas 2026)\n"]

for return_date in RETURN_DATES:
    lines.append("=" * 60)
    lines.append(f"📅 RETURN DATE: {return_date}")
    lines.append("=" * 60)

    # ── STEP 1: Outbound search ───────────────────────────────────
    outbound_results = client.search({
        "engine": "google_flights",
        "departure_id": "LHR",
        "arrival_id": "HKG",
        "currency": "GBP",
        "type": "1",
        "gl": "uk",
        "adults": "3",
        "sort_by": "2",
        "stops": "2",
        "layover_duration": "0,360",
        "outbound_date": "2026-12-24",
        "return_date": return_date
    })

    outbound_data = dict(outbound_results)
    all_outbound = outbound_data.get("best_flights", []) + outbound_data.get("other_flights", [])

    if not all_outbound:
        lines.append("  ⚠️ No outbound flights found.\n")
        continue

    # Sort by price, pick cheapest
    all_outbound.sort(key=lambda f: f.get("price", 999999))
    cheapest_outbound = all_outbound[0]
    dep_token = cheapest_outbound.get("departure_token")

    lines.append("\n🛫 OUTBOUND — LHR → HKG (24 Dec 2026) [Cheapest]")
    lines.append(format_flight_details(cheapest_outbound))

    # ── STEP 2: Return search using departure_token ───────────────
    if dep_token:
        return_results = client.search({
            "engine": "google_flights",
            "departure_id": "LHR",
            "arrival_id": "HKG",
            "currency": "GBP",
            "type": "1",
            "gl": "uk",
            "adults": "3",
            "sort_by": "2",
            "stops": "2",
            "layover_duration": "0,360",
            "outbound_date": "2026-12-24",
            "return_date": return_date,
            "departure_token": dep_token
        })

        return_data = dict(return_results)
        all_return = return_data.get("best_flights", []) + return_data.get("other_flights", [])

        if all_return:
            all_return.sort(key=lambda f: f.get("price", 999999))
            cheapest_return = all_return[0]

            lines.append(f"\n🛬 RETURN — HKG → LHR ({return_date}) [Cheapest paired return]")
            lines.append(format_flight_details(cheapest_return))

            # Store for top 3 summary
            out_price = cheapest_outbound.get("price", 0)
            ret_price = cheapest_return.get("price", 0)
            total_price = out_price + ret_price if isinstance(out_price, (int, float)) and isinstance(ret_price, (int, float)) else "N/A"

            out_legs = cheapest_outbound.get("flights", [])
            ret_legs = cheapest_return.get("flights", [])
            out_airline = " → ".join(leg.get("airline", "?") for leg in out_legs)
            ret_airline = " → ".join(leg.get("airline", "?") for leg in ret_legs)

            all_trips.append({
                "return_date": return_date,
                "total_price": total_price,
                "out_airline": out_airline,
                "ret_airline": ret_airline,
            })
        else:
            lines.append("\n  ⚠️ No return flights found for this token.\n")
    else:
        lines.append("\n  ⚠️ No departure_token — skipping return search.\n")

    lines.append("")

# ── TOP 3 CHEAPEST OVERALL ────────────────────────────────────────────
lines.append("=" * 60)
lines.append("🏆 TOP 3 CHEAPEST ROUND TRIPS (across all return dates)")
lines.append("=" * 60)

valid_trips = [t for t in all_trips if isinstance(t["total_price"], (int, float))]
valid_trips.sort(key=lambda t: t["total_price"])

if not valid_trips:
    lines.append("  No complete round-trip data available.")
else:
    for i, trip in enumerate(valid_trips[:3], 1):
        lines.append(f"\n  #{i} — Return date: {trip['return_date']}")
        lines.append(f"       Total Price:    £{trip['total_price']}")
        lines.append(f"       Outbound:       {trip['out_airline']}")
        lines.append(f"       Return:         {trip['ret_airline']}")

lines.append("")

# ── Write to file ─────────────────────────────────────────────────────
summary = "\n".join(lines)
print(summary)

with open("results.txt", "w", encoding="utf-8") as f:
    f.write(summary)

print("\nresults.txt written.")
