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
  "gl": "uk",
  "adults": "3",
  "sort_by": "2",
  "stops": "2",
  "layover_duration": "0,360",
  "outbound_date": "2026-12-24",
  "return_date": "2027-01-21"
  
  
})

print(json.dumps(dict(results), indent=2))
