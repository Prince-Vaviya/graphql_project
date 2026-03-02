import json
from schema import schema
from database import Base, engine, SessionLocal
from main import init_db

Base.metadata.create_all(bind=engine)
init_db()

class MockRequest:
    def __init__(self):
        self.state = type('State', (), {'db': SessionLocal()})()

def run_query(query):
    context = {"request": MockRequest()}
    result = schema.execute(query, context_value=context)
    context["request"].state.db.close()
    
    data = {}
    if result.errors:
        data["errors"] = [str(e) for e in result.errors]
    if result.data:
        data["data"] = result.data
    return data



queries = [
    ("Get Categories", """
    query {
      categories {
        id
        name
        items {
          name
          price
          available
        }
      }
    }
    """),
    ("Create Order", """
    mutation {
      createOrder(input: {
        customerId: 1
        tableId: 1
        items: [
          { menuItemId: 1, quantity: 2 }
          { menuItemId: 5, quantity: 1 }
        ]
      }) {
        order {
          id
          orderDate
          totalAmount
          status
        }
      }
    }
    """),
    ("Get Orders", """
    query {
      orders(status: "pending") {
        id
        orderDate
        table { tableNumber }
        items {
          menuItem { name }
          quantity
        }
      }
    }
    """),
    ("Update Status", """
    mutation {
      updateOrderStatus(input: {
        orderId: 1
        status: "ready"
      }) {
        order {
          id
          status
        }
      }
    }
    """),
    ("Customer", """
    query {
      customer(id: 1) {
        name
        loyaltyPoints
        orders {
          id
          orderDate
          totalAmount
          status
        }
      }
    }
    """)
]

for name, q in queries:
    print(f"--- {name} ---")
    print(json.dumps(run_query(q), indent=2))
