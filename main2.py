import serpapi
import json
import os

client = serpapi.Client(api_key=os.environ["SERPAPI_KEY"])
results = client.search({
  "engine": "google_flights",
  "departure_id": "LHR",
  "arrival_id": "HKG",
  "currency": "GBP",
  "type": "1",
  "outbound_date": "2026-12-24",
  "return_date": "2027-01-21"
})

print(json.dumps(results, indent=2))
