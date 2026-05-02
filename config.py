from pymongo import MongoClient

# 🔴 Replace with your MongoDB Atlas connection string
MONGO_URI = "mongodb+srv://admin:admin@cluster0.npzib2n.mongodb.net/?appName=Cluster0"

client = MongoClient(MONGO_URI)
db = client["rental_db"]

flats_collection = db["flats"]
tenants_collection = db["tenants"]
rent_collection = db["rent_records"]
status_collection = db["flat_status"]