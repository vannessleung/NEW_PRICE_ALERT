import serpapi
import os

client = serpapi.Client(api_key=os.environ["SERPAPI_KEY"])

GO_PRICE = 1700
alerts = []
lines = []
RETURN_DATES = [
    "2027-01-18",
    "2027-01-19",
    "2027-01-20",
    "2027-01-21",
    "2027-01-22",
    "2027-01-23",
    "2027-01-24",
]

def mins_to_hm(mins):
    """Convert minutes to e.g. 14h 30m"""
    if not isinstance(mins, (int, float)):
        return str(mins)
    h, m = divmod(int(mins), 60)
    return f"{h}h {m}m"

def format_flight_details(flight):
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
            layover_parts.append(f"{airport} ({code}), {mins_to_hm(duration)}")
        layover_str = " | ".join(layover_parts)
    else:
        layover_str = "Direct (no layover)"

    lines = []
    lines.append(f"   Airlines:         {airlines}")
    lines.append(f"   Price:            £{price}")
    lines.append(f"   Total Duration:   {mins_to_hm(total_duration)}")
    lines.append(f"   Layover(s):       {layover_str}")
    return "\n".join(lines)

all_trips = []  # for top 3 summary across all dates


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

    all_outbound.sort(key=lambda f: f.get("price", 999999))

    # ── Top 3 outbound flights ────────────────────────────────────
    for rank, outbound_flight in enumerate(all_outbound[:3], 1):
        dep_token = outbound_flight.get("departure_token")
        out_price = outbound_flight.get("price", "N/A")

        lines.append(f"\n🛫 OUTBOUND #{rank} — LHR → HKG (24 Dec 2026)")
        lines.append(format_flight_details(outbound_flight))

        # ── STEP 2: Return search for this outbound ───────────────
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

                lines.append(f"\n🛬 RETURN — HKG → LHR ({return_date}) [Cheapest paired]")
                lines.append(format_flight_details(cheapest_return))

                # The price returned already represents the full round trip
                total_price = cheapest_return.get("price", "N/A")

                out_legs = outbound_flight.get("flights", [])
                ret_legs = cheapest_return.get("flights", [])
                out_airline = " → ".join(leg.get("airline", "?") for leg in out_legs)
                ret_airline = " → ".join(leg.get("airline", "?") for leg in ret_legs)

                if isinstance(total_price, (int, float)) and total_price < GO_PRICE:
                    alerts.append(f"🚨 OH MY GOD WE NEED TO GO NOW — {return_date} outbound #{rank}: £{total_price}")

                lines.append(f"\n   💰 Round-trip total: £{total_price}")

                all_trips.append({
                    "return_date": return_date,
                    "outbound_rank": rank,
                    "total_price": total_price,
                    "out_airline": out_airline,
                    "ret_airline": ret_airline,
                })
            else:
                lines.append("\n  ⚠️ No return flights found for this token.")
        else:
            lines.append("\n  ⚠️ No departure_token — skipping return search.")

        lines.append("")

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
        lines.append(f"\n  #{i} — Return date: {trip['return_date']} (Outbound option #{trip['outbound_rank']})")
        lines.append(f"       Total Price:    £{trip['total_price']}")
        lines.append(f"       Outbound:       {trip['out_airline']}")
        lines.append(f"       Return:         {trip['ret_airline']}")

lines.append("")

# ── Write to file ─────────────────────────────────────────────────────

# ── Write to file ─────────────────────────────────────────────────────
alert_banner = "\n".join(alerts) + "\n\n" if alerts else ""
lines.insert(0, alert_banner + "LHR ⇄ HKG Flight Search\n")

summary = "\n".join(lines)
print(summary)

with open("results.txt", "w", encoding="utf-8") as f:
    f.write(summary)

print("\nresults.txt written.")
