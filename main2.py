import serpapi

client = serpapi.Client(api_key="SERPAPI_KEY")
results = client.search({
  "engine": "google_flights",
  "departure_id": "CDG",
  "arrival_id": "AUS",
  "currency": "USD",
  "type": "2",
  "outbound_date": "2026-06-16"
})
best_flights = results["best_flights"]
