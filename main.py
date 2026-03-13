from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from database import engine, SessionLocal
from models import Base, Order
import uvicorn
import os

Base.metadata.create_all(bind=engine)

app = FastAPI()

# Serve CSS / JS files
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

# -------------------------------
# MENU PRICES (single source)
# -------------------------------

MENU = {
    "Cappuccino": 180,
    "Latte": 200,
    "Paneer Sandwich": 250,
    "Alfredo Pasta": 320,
    "Blueberry Cheesecake": 280
}

# -------------------------------
# CART STORAGE (table based)
# -------------------------------

cart = {}

# -------------------------------
# HEALTH CHECK
# -------------------------------

@app.api_route("/health", methods=["GET", "HEAD"])
def health():
    return {"status": "ok"}

# -------------------------------
# HOME
# -------------------------------

@app.get("/")
def home():
    return RedirectResponse("/table/1")

# -------------------------------
# CUSTOMER ENTRY
# -------------------------------

@app.get("/table/{table_id}", response_class=HTMLResponse)
def customer_details(request: Request, table_id: int):

    return templates.TemplateResponse(
        "customer.html",
        {
            "request": request,
            "table_id": table_id
        }
    )

@app.post("/start-order")
def start_order(
    table_id: int = Form(...),
    customer_name: str = Form(...),
    customer_phone: str = Form(...)
):

    return RedirectResponse(
        f"/menu/{table_id}?name={customer_name}&phone={customer_phone}",
        status_code=303
    )

# -------------------------------
# MENU
# -------------------------------

@app.get("/menu/{table_id}", response_class=HTMLResponse)
def menu(
    request: Request,
    table_id: int,
    name: str = "",
    phone: str = "",
    staff_called: int = 0
):

    return templates.TemplateResponse(
        "menu.html",
        {
            "request": request,
            "table_id": table_id,
            "name": name,
            "phone": phone,
            "staff_called": staff_called
        }
    )

# -------------------------------
# ADD TO CART
# -------------------------------

@app.post("/add-to-cart")
def add_to_cart(
    table_id: int = Form(...),
    customer_name: str = Form(...),
    customer_phone: str = Form(...),
    item: str = Form(...)
):

    if table_id not in cart:
        cart[table_id] = []

    cart[table_id].append({
        "table_id": table_id,
        "name": customer_name,
        "phone": customer_phone,
        "item": item
    })

    return {"status": "ok"}

# -------------------------------
# CART PAGE
# -------------------------------

@app.get("/cart", response_class=HTMLResponse)
def cart_page(request: Request, name: str, phone: str, table: int):

    table_cart = cart.get(table, [])

    items = []
    total = 0

    for item in table_cart:

        price = MENU.get(item["item"], 0)

        items.append({
            "item": item["item"],
            "price": price
        })

        total += price

    return templates.TemplateResponse(
        "cart.html",
        {
            "request": request,
            "cart": items,
            "name": name,
            "phone": phone,
            "table": table,
            "total": total
        }
    )

# -------------------------------
# PLACE ORDER
# -------------------------------

@app.post("/place-order")
def place_order():

    if not cart:
        return RedirectResponse("/", status_code=303)

    table_id = list(cart.keys())[0]
    table_cart = cart.get(table_id, [])

    name = table_cart[0]["name"]
    phone = table_cart[0]["phone"]

    db = SessionLocal()

    try:

        for item in table_cart:

            order = Order(
                table_id=item["table_id"],
                customer_name=item["name"],
                customer_phone=item["phone"],
                item=item["item"],
                status="NEW"
            )

            db.add(order)

        db.commit()

    finally:
        db.close()

    cart[table_id] = []

    return RedirectResponse(
        f"/order-confirmed?table={table_id}&name={name}&phone={phone}",
        status_code=303
    )

# -------------------------------
# ORDER CONFIRMATION
# -------------------------------

@app.get("/order-confirmed", response_class=HTMLResponse)
def order_confirmed(request: Request, table:int, name:str, phone:str):

    return templates.TemplateResponse(
        "order_confirmed.html",
        {
            "request": request,
            "table": table,
            "name": name,
            "phone": phone
        }
    )

# -------------------------------
# CALL STAFF
# -------------------------------

@app.post("/call-staff")
def call_staff(
    table_id: int = Form(...),
    name: str = Form(...),
    phone: str = Form(...)
):

    print(f"Table {table_id} needs staff")

    return RedirectResponse(
        f"/menu/{table_id}?name={name}&phone={phone}&staff_called=1",
        status_code=303
    )

# -------------------------------
# KITCHEN DASHBOARD
# -------------------------------

@app.get("/kitchen", response_class=HTMLResponse)
def kitchen(request: Request):

    db = SessionLocal()

    try:
        orders = db.query(Order).filter(Order.status != "SERVED").all()
    finally:
        db.close()

    tables = {}

    for order in orders:

        if order.table_id not in tables:

            tables[order.table_id] = {
                "customer": order.customer_name,
                "items": []
            }

        tables[order.table_id]["items"].append(order.item)

    return templates.TemplateResponse(
        "kitchen.html",
        {
            "request": request,
            "tables": tables
        }
    )

# -------------------------------
# STAFF DASHBOARD
# -------------------------------

@app.get("/staff", response_class=HTMLResponse)
def staff(request: Request):

    db = SessionLocal()

    try:
        orders = db.query(Order).all()
    finally:
        db.close()

    return templates.TemplateResponse(
        "staff.html",
        {"request": request, "orders": orders}
    )

# -------------------------------
# CUSTOMER BILL
# -------------------------------

@app.get("/bill-customer", response_class=HTMLResponse)
def customer_bill(request: Request, table: int, name: str, phone: str):

    db = SessionLocal()

    try:
        orders = db.query(Order).filter(Order.table_id == table).all()
    finally:
        db.close()

    items = []
    total = 0

    for order in orders:

        price = MENU.get(order.item, 0)

        items.append({
            "name": order.item,
            "price": price
        })

        total += price

    return templates.TemplateResponse(
        "bill_customer.html",
        {
            "request": request,
            "items": items,
            "total": total,
            "table": table,
            "name": name
        }
    )

# -------------------------------
# PAYMENT
# -------------------------------

@app.post("/pay")
def pay():

    return RedirectResponse("/feedback", status_code=303)

# -------------------------------
# FEEDBACK
# -------------------------------

@app.get("/feedback", response_class=HTMLResponse)
def feedback(request: Request):

    return templates.TemplateResponse(
        "feedback.html",
        {"request": request}
    )

@app.post("/submit-feedback")
def submit_feedback():

    return RedirectResponse("/thankyou", status_code=303)

# -------------------------------
# THANK YOU
# -------------------------------

@app.get("/thankyou", response_class=HTMLResponse)
def thankyou(request: Request):

    return templates.TemplateResponse(
        "thankyou.html",
        {"request": request}
    )

# -------------------------------
# RUN SERVER
# -------------------------------

if __name__ == "__main__":

    port = int(os.environ.get("PORT", 10000))

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port
    )