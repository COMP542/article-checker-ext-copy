# Start the Flask backend:
cd backend
bash run.sh

# Test Curl
curl -X POST http://127.0.0.1:5000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Israeli airstrike kills civilians in Gaza hospital",
    "text": "An Israeli airstrike struck a hospital in Gaza on Tuesday, killing an unconfirmed number of civilians according to Hamas health officials. Israel confirmed the strike targeted a militant command center operating beneath the facility. Palestinian authorities claim at least 50 people were killed, while Israeli military sources say the number is unverified. Several witnesses reportedly saw missiles hit the building, though the exact death toll remains unknown. The strike has been condemned by multiple governments."
  }'

