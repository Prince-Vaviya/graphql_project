from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from schema import schema
from database import engine, Base, SessionLocal
import models

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Restaurant Order System API")

@app.middleware("http")
async def db_session_middleware(request: Request, call_next):
    request.state.db = SessionLocal()
    try:
        response = await call_next(request)
        return response
    finally:
        request.state.db.close()

@app.post("/graphql")
async def graphql_endpoint(request: Request):
    data = await request.json()
    query = data.get("query")
    variables = data.get("variables", {})
    operation_name = data.get("operationName")
    
    result = schema.execute(
        query,
        variable_values=variables,
        operation_name=operation_name,
        context_value={"request": request}
    )
    
    response_data = {"data": result.data}
    if result.errors:
        response_data["errors"] = [str(err) for err in result.errors]
        
    return response_data

@app.get("/graphql")
async def graphiql_endpoint():
    html = """
    <!DOCTYPE html>
    <html>
      <head>
        <title>GraphiQL</title>
        <link rel="stylesheet" href="https://unpkg.com/graphiql/graphiql.min.css" />
      </head>
      <body style="margin: 0; padding: 0;">
        <div id="graphiql" style="height: 100vh;"></div>
        <script src="https://unpkg.com/react/umd/react.production.min.js"></script>
        <script src="https://unpkg.com/react-dom/umd/react-dom.production.min.js"></script>
        <script src="https://unpkg.com/graphiql/graphiql.min.js"></script>
        <script>
          const fetcher = GraphiQL.createFetcher({ url: '/graphql' });
          ReactDOM.render(
            React.createElement(GraphiQL, { fetcher: fetcher }),
            document.getElementById('graphiql'),
          );
        </script>
      </body>
    </html>
    """
    return HTMLResponse(html)

def init_db():
    db = SessionLocal()
    if not db.query(models.Category).first():
        cat1 = models.Category(name="Starters", description="Start your meal", display_order=1)
        cat2 = models.Category(name="Mains", description="Main courses", display_order=2)
        db.add(cat1)
        db.add(cat2)
        db.commit()

        c1 = models.Customer(name="John Doe", email="j@d.com", phone="123", loyalty_points=0)
        db.add(c1)
        
        t1 = models.Table(table_number=1, capacity=4, location="Window")
        t2 = models.Table(table_number=2, capacity=2, location="Center")
        db.add(t1)
        db.add(t2)
        
        m1 = models.MenuItem(name="Soup", price=5.0, category_id=cat1.id, available=True)
        m2 = models.MenuItem(name="Salad", price=7.0, category_id=cat1.id, available=False)
        m3 = models.MenuItem(name="Steak", price=25.0, category_id=cat2.id, available=True)
        m4 = models.MenuItem(name="Pasta", price=15.0, category_id=cat2.id, available=True)
        m5 = models.MenuItem(name="Burger", price=12.0, category_id=cat2.id, available=True)
        
        db.add_all([m1, m2, m3, m4, m5])
        db.commit()
    db.close()

@app.on_event("startup")
def startup_event():
    init_db()
