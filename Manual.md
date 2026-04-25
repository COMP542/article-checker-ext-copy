# Start the Flask backend:
cd backend
bash run.sh

# Test Curl
curl -X POST http://127.0.0.1:5000/analyze \
  -H "Content-Type: application/json" \
  -d '{"title": "Climate change threatens coastal cities as sea levels rise", "text": "Scientists warn that rising sea levels caused by climate change pose an existential threat to coastal cities worldwide. New research shows that without immediate action to reduce carbon emissions, millions of people could be displaced by 2050."}'