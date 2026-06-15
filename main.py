import re
import base64
from datetime import date, timedelta
from playwright.sync_api import sync_playwright

# ================================
# CONFIG
# ================================
ORIGINAL_TFS = "CBwQAhoxEgoyMDI2LTEyLTI0KAFgqApqDAgDEggvbS8wNGpwbHIMCAMSCC9tLzAzaDY0kAGGAxoxEgoyMDI3LTAxLTIxKAFgqApqDAgDEggvbS8wM2g2NHIMCAMSCC9tLzA0anBskAGGA0ABQAFAAUgBcAGCAQsI____________AZgBAQ&tfu=EgoIABAAGAAgAigB"
ORIGINAL_RETURN_DATE = "2027-01-21"

RETURN_DATE_START = date(2027, 1, 18)
RETURN_DATE_END   = date(2027, 1, 24)


# ================================
# URL GENERATION
# ================================
def make_url(return_date_str: str) -> str:
    tfs_only = ORIGINAL_TFS.split("&")[0]  # strip anything after & just in case
    padding = (4 - len(tfs_only) % 4) % 4
    decoded = base64.urlsafe_b64decode(tfs_only + "=" * padding)
    updated = decoded.replace(ORIGINAL_RETURN_DATE.encode(), return_date_str.encode())
    tfs = base64.urlsafe_b64encode(updated).decode().rstrip("=")
    return f"https://www.google.com/travel/flights/search?tfs={tfs}&tfu=EgoIABAAGAAgAigB&hl=en-GB&gl=GB"


def return_dates():
    delta = RETURN_DATE_END - RETURN_DATE_START
    return [str(RETURN_DATE_START + timedelta(days=i)) for i in range(delta.days + 1)]


# ================================
# PARSING
# ================================
def extract_price(line):
    match = re.search(r'£\d{1,3}(?:,\d{3})*', line)
    if match:
        return int(match.group().replace("£", "").replace(",", ""))
    return None


def parse_flights(text, return_date):
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    # Remove UI noise
    cleaned = []
    for l in lines:
        if any(x in l for x in [
            "Skip to main content", "Fetching results",
            "Checking prices", "Searching", "Other departing flights"
        ]):
            continue
        cleaned.append(l)

    # Split into cards
    cards = []
    current = []
    started = False
    for line in cleaned:
        if re.match(r"\d{2}:\d{2}", line):
            started = True
        if not started:
            continue
        current.append(line)
        if "round trip" in line:
            cards.append(current)
            current = []

    # Parse each card
    flights = []
    for card in cards:
        flight = {
            "return_date": return_date,
            "airline": None,
            "departure": None,
            "arrival": None,
            "route": None,
            "stops": None,
            "duration": None,
            "transfer": None,
            "price": None,
        }

        for line in card:
            price = extract_price(line)
            if price:
                flight["price"] = price
                continue

            if re.match(r"\d{2}:\d{2}", line):
                if flight["departure"] is None:
                    flight["departure"] = line
                else:
                    flight["arrival"] = line
                continue

            if "hrs" in line:
                transfer_match = re.search(r"(\d+\s*hrs\s*\d+\s*min)\s*([A-Z]{3})", line)
                if transfer_match:
                    flight["transfer"] = line
                    continue
                total_match = re.fullmatch(r"\d+\s*hrs\s*\d+\s*min", line)
                if total_match:
                    flight["duration"] = line
                    continue

            if "LHR" in line and "–" in line:
                flight["route"] = line
                continue

            if "stop" in line.lower():
                flight["stops"] = line
                continue

            if (
                "£" not in line and "hrs" not in line and
                "stop" not in line.lower() and "–" not in line and
                "CO2" not in line and not line.isdigit() and
                not re.match(r"\d{2}:\d{2}", line) and
                not re.match(r"\d{2}:\d{2}\+\d", line) and
                len(line) < 60
            ):
                if flight["airline"] is None:
                    flight["airline"] = line

        if flight["price"] is not None:
            flights.append(flight)

    return flights


# ================================
# MAIN
# ================================
def check_prices():
    all_flights = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for return_date in return_dates():
            print(f"Scraping {return_date}...")
            page.goto(make_url(return_date))
            page.wait_for_timeout(10000)

            text = page.inner_text("body")
            flights = parse_flights(text, return_date)
            print(f"  → {len(flights)} flights found")
            all_flights.extend(flights)

        browser.close()

    all_flights.sort(key=lambda x: x["price"])

    # Build by_date dict
    from collections import defaultdict
    by_date = defaultdict(list)
    for f in all_flights:
        by_date[f["return_date"]].append(f)
    PRICE_ALERT = 1700
            
    with open("results.txt", "w", encoding="utf-8") as f:
        # Alert check
        if all_flights and all_flights[0]["price"] < PRICE_ALERT:
            f.write("🚨 OH MY GOD WE NEED TO FLY NOW 🚨\n")
            f.write(f"Cheapest flight is £{all_flights[0]['price']} — below your £{PRICE_ALERT} threshold!\n\n")

        f.write("===== TOP 5 CHEAPEST ACROSS ALL DATES =====\n")
        for flight in all_flights[:5]:
            f.write(format_flight(flight) + "\n")

        f.write("\n===== TOP 3 CHEAPEST PER RETURN DATE =====\n")
        for d in sorted(by_date):
            f.write(f"\n{d}:\n")
            for flight in by_date[d][:3]:
                f.write(format_flight(flight) + "\n")

    print("\n===== CHEAPEST PER RETURN DATE =====")
    seen = {}
    for f in all_flights:
        if f["return_date"] not in seen:
            seen[f["return_date"]] = f
    for d in sorted(seen):
        print(f"  {d}: £{seen[d]['price']} — {seen[d]['airline']}")


def format_flight(f):
    lines = []
    lines.append(f"  💰 £{f['price']} — {f['airline'] or 'Unknown airline'}")
    lines.append(f"  📅 Return: {f['return_date']}")
    if f['departure'] and f['arrival']:
        lines.append(f"  🕐 {f['departure']} → {f['arrival']}")
    if f['duration']:
        lines.append(f"  ⏱  Total duration: {f['duration']}")
    if f['stops']:
        lines.append(f"  🔁 {f['stops']}")
    if f['transfer']:
        lines.append(f"  ✈  Via: {f['transfer']}")
    if f['route']:
        lines.append(f"  🗺  Route: {f['route']}")
    lines.append("")  # blank line between flights
    return "\n".join(lines)
    


check_prices()
