from pymongo import MongoClient

# 🔴 Replace with your MongoDB Atlas connection string
MONGO_URI = "mongodb://localhost:27017/"

client = MongoClient(MONGO_URI)
db = client["rental_db"]

flats_collection = db["flats"]
tenants_collection = db["tenants"]
rent_collection = db["rent_records"]
status_collection = db["flat_status"]