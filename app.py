from flask import Flask, render_template, request, redirect, url_for
from config import flats_collection, tenants_collection, rent_collection, status_collection
from datetime import datetime

app = Flask(__name__)

# 🔴 INITIAL FLATS (RUN ONCE)
def initialize_flats():
    flats = ["101","102","103","401","402","701","702","901","904",
             "905","906","907","908","1001","1101","1105","1106","1107"]

    for f in flats:
        if not flats_collection.find_one({"flat_id": f}):
            flats_collection.insert_one({
                "flat_id": f,
                "current_tenant_id": None
            })

# ---------------- MAIN PAGE ----------------

@app.route("/", methods=["GET", "POST"])
def index():
    month = int(request.form.get("month", datetime.now().month))
    year = int(request.form.get("year", datetime.now().year))

    flats = list(flats_collection.find())

    # 🔥 Attach tenant name + alert
    for flat in flats:
        tenant_id = flat.get("current_tenant_id")

        if tenant_id:
            tenant = tenants_collection.find_one({"_id": tenant_id})

            if tenant:
                flat["tenant_name"] = tenant.get("name", "Unknown")

                # 🔴 ALERT LOGIC
                alert = False
                end_str = tenant.get("agreement_end_date")

                if end_str:
                    try:
                        end_date = datetime.strptime(end_str, "%Y-%m-%d")

                        if datetime.now() > end_date and not tenant.get("rent_increased"):
                            alert = True
                    except:
                        alert = False

                flat["alert"] = alert
            else:
                flat["tenant_name"] = "Unknown"
                flat["alert"] = False
        else:
            flat["tenant_name"] = None
            flat["alert"] = False

    # 📊 DASHBOARD
    dashboard = {
        "expected": 0,
        "received": 0,
        "paid_flats": [],
        "pending_flats": [],
        "empty_count": 0
    }

    for flat in flats:
        flat_id = flat["flat_id"]

        # ✅ Check empty
        empty = status_collection.find_one({
            "flat_id": flat_id,
            "month": month,
            "year": year
        })

        if empty:
            dashboard["empty_count"] += 1
            continue

        tenant_id = flat.get("current_tenant_id")

        if tenant_id:
            tenant = tenants_collection.find_one({"_id": tenant_id})

            if tenant:
                start_str = tenant.get("agreement_start_date")

                # ✅ Handle missing start date
                if start_str:
                    start = datetime.strptime(start_str, "%Y-%m-%d")
                else:
                    start = datetime(2000, 1, 1)

                end_str = tenant.get("actual_end_date")
                if end_str:
                    end = datetime.strptime(end_str, "%Y-%m-%d")
                else:
                    end = None

                current_month_date = datetime(year, month, 1)

                if start <= current_month_date and (end is None or end >= current_month_date):

                    dashboard["expected"] += tenant.get("rent", 0)

                    rent = rent_collection.find_one({
                        "flat_id": flat_id,
                        "month": month,
                        "year": year
                    })

                    if rent:
                        dashboard["received"] += rent.get("amount", 0)
                        dashboard["paid_flats"].append(flat_id)
                    else:
                        dashboard["pending_flats"].append(flat_id)

    return render_template(
        "index.html",
        flats=flats,
        dashboard=dashboard,
        month=month,
        year=year
    )



# ---------------- ADD TENANT ----------------
@app.route("/add_tenant/<flat_id>", methods=["GET","POST"])
def add_tenant(flat_id):
    if request.method == "POST":
        tenant = {
             "flat_id": flat_id,
            "name": request.form["name"],
            # ✅ Required
            "rent": int(request.form["rent"]) if request.form["rent"] else 0,
            # ✅ Optional
            "deposit": int(request.form["deposit"]) if request.form["deposit"] else 0,
            "phone": request.form["phone"] or None,
            "aadhaar": request.form["aadhaar"] or None,
            "pan": request.form["pan"] or None,

            "agreement_start_date": request.form["start_date"] or None,
            "agreement_end_date": request.form["end_date"] or None,

            "stayed_after_end": request.form.get("stayed") == "yes",
            "rent_increased": request.form.get("increased") == "yes",

            "actual_end_date": None,
            "is_active": True
}

        result = tenants_collection.insert_one(tenant)

        flats_collection.update_one(
            {"flat_id": flat_id},
            {"$set": {"current_tenant_id": result.inserted_id}}
        )

        return redirect(url_for("index"))

    return render_template("add_tenant.html", flat_id=flat_id)


# ---------------- RENT ENTRY ----------------
@app.route("/rent/<flat_id>", methods=["GET","POST"])
def rent(flat_id):
    if request.method == "POST":
        flat = flats_collection.find_one({"flat_id": flat_id})

        rent_collection.insert_one({
            "flat_id": flat_id,
            "tenant_id": str(flat["current_tenant_id"]),
            "month": int(request.form["month"]),
            "year": int(request.form["year"]),
            "amount": int(request.form["amount"]),
            "received_by": request.form["received_by"],
            "date": request.form["date"],
            "late_penalty": int(request.form["penalty"]),
            "remarks": request.form["remarks"]
        })

        return redirect(url_for("index"))

    return render_template("rent_entry.html", flat_id=flat_id)


# ---------------- MARK EMPTY ----------------
@app.route("/empty/<flat_id>", methods=["POST"])
def empty(flat_id):
    month = int(request.form["month"])
    year = int(request.form["year"])

    existing = status_collection.find_one({
        "flat_id": flat_id,
        "month": month,
        "year": year
    })

    if existing:
        status_collection.delete_one({"_id": existing["_id"]})
    else:
        status_collection.insert_one({
            "flat_id": flat_id,
            "month": month,
            "year": year,
            "is_empty": True
        })

    return redirect(url_for("index"))


# ---------------- FLAT DETAILS ----------------
@app.route("/flat/<flat_id>")
def flat_details(flat_id):
    tenants = list(tenants_collection.find({"flat_id": flat_id}))
    return render_template("flat.html", flat_id=flat_id, tenants=tenants)


# ---------------- TENANT DETAILS ----------------
@app.route("/tenant/<tenant_id>")
def tenant_details(tenant_id):
    from bson import ObjectId

    tenant = tenants_collection.find_one({"_id": ObjectId(tenant_id)})

    rent_history = list(rent_collection.find({
        "tenant_id": str(tenant_id)
    }))

    return render_template("tenant_details.html", tenant=tenant, rent_history=rent_history)


# ---------------- CLOSE TENANT ----------------
@app.route("/close_tenant/<tenant_id>", methods=["GET","POST"])
def close_tenant(tenant_id):
    from bson import ObjectId

    tenant = tenants_collection.find_one({"_id": ObjectId(tenant_id)})

    if request.method == "POST":
        tenants_collection.update_one(
            {"_id": ObjectId(tenant_id)},
            {
                "$set": {
                    "actual_end_date": request.form["end_date"],
                    "damage": request.form["damage"],
                    "deposit_returned": request.form["deposit"],
                    "closing_remarks": request.form["remarks"],
                    "is_active": False
                }
            }
        )

        flats_collection.update_one(
            {"flat_id": tenant["flat_id"]},
            {"$set": {"current_tenant_id": None}}
        )

        return redirect(url_for("index"))

    return render_template("close_tenant.html", tenant=tenant)

# ---------------- EDIT TENANT ----------------
@app.route("/edit_tenant/<tenant_id>", methods=["GET", "POST"])
def edit_tenant(tenant_id):
    from bson import ObjectId

    tenant = tenants_collection.find_one({"_id": ObjectId(tenant_id)})

    if not tenant:
        return "Tenant not found"

    if request.method == "POST":
        tenants_collection.update_one(
            {"_id": ObjectId(tenant_id)},
            {
                "$set": {
                    # ❌ NOT EDITABLE
                    # flat_id and name are locked

                    # ✅ Editable fields
                    "rent": int(request.form["rent"]) if request.form["rent"] else 0,
                    "deposit": int(request.form["deposit"]) if request.form["deposit"] else 0,
                    "phone": request.form["phone"] or None,
                    "aadhaar": request.form["aadhaar"] or None,
                    "pan": request.form["pan"] or None,

                    "agreement_start_date": request.form["start_date"] or None,
                    "agreement_end_date": request.form["end_date"] or None,

                    "stayed_after_end": request.form.get("stayed") == "yes",
                    "rent_increased": request.form.get("increased") == "yes"
                }
            }
        )

        return redirect(url_for("tenant_details", tenant_id=tenant_id))

    return render_template("edit_tenant.html", tenant=tenant)

if __name__ == "__main__":
    initialize_flats()
    app.run(host="0.0.0.0", port=10000)