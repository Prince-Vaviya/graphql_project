import graphene
import models

def get_db(info):
    return info.context["request"].state.db

class MenuItemType(graphene.ObjectType):
    id = graphene.Int()
    name = graphene.String()
    description = graphene.String()
    price = graphene.Float()
    category_id = graphene.Int()
    available = graphene.Boolean()
    preparation_time = graphene.Int()

class CategoryType(graphene.ObjectType):
    id = graphene.Int()
    name = graphene.String()
    description = graphene.String()
    display_order = graphene.Int()
    items = graphene.List(MenuItemType)

    def resolve_items(parent, info):
        return parent.items

class TableType(graphene.ObjectType):
    id = graphene.Int()
    table_number = graphene.Int()
    capacity = graphene.Int()
    location = graphene.String()

class OrderItemType(graphene.ObjectType):
    id = graphene.Int()
    order_id = graphene.Int()
    menu_item_id = graphene.Int()
    quantity = graphene.Int()
    price_at_order = graphene.Float()
    
    menu_item = graphene.Field(MenuItemType)
    
    def resolve_menu_item(parent, info):
        return parent.menu_item

class OrderType(graphene.ObjectType):
    id = graphene.Int()
    customer_id = graphene.Int()
    table_id = graphene.Int()
    order_date = graphene.DateTime()
    status = graphene.String()
    total_amount = graphene.Float()
    
    table = graphene.Field(TableType)
    items = graphene.List(OrderItemType)

    def resolve_table(parent, info):
        return parent.table
        
    def resolve_items(parent, info):
        return parent.items

class CustomerType(graphene.ObjectType):
    id = graphene.Int()
    name = graphene.String()
    email = graphene.String()
    phone = graphene.String()
    loyalty_points = graphene.Int()
    orders = graphene.List(OrderType)
    
    def resolve_orders(parent, info):
        return parent.orders

class OrderItemInput(graphene.InputObjectType):
    menu_item_id = graphene.Int(required=True)
    quantity = graphene.Int(default_value=1)

class CreateOrderInput(graphene.InputObjectType):
    customer_id = graphene.Int(required=True)
    table_id = graphene.Int(required=True)
    items = graphene.List(OrderItemInput, required=True)

class CreateOrderPayload(graphene.ObjectType):
    order = graphene.Field(OrderType)

class CreateOrder(graphene.Mutation):
    class Arguments:
        input = CreateOrderInput(required=True)

    Output = CreateOrderPayload

    def mutate(self, info, input):
        db = get_db(info)
        table = db.query(models.Table).filter(models.Table.id == input.table_id).first()
        if not table:
            raise Exception("Table not found")
            
        new_order = models.Order(
            customer_id=input.customer_id,
            table_id=input.table_id,
            status="pending",
            total_amount=0.0
        )
        
        db.add(new_order)
        db.flush() 
        
        total_amount = 0.0
        
        for item_input in input.items:
            menu_item = db.query(models.MenuItem).filter(models.MenuItem.id == item_input.menu_item_id).first()
            if not menu_item:
                raise Exception(f"Item {item_input.menu_item_id} not found")
            
            if not menu_item.available:
                raise Exception(f"Item {menu_item.name} is not available")
                
            order_item = models.OrderItem(
                order_id=new_order.id,
                menu_item_id=menu_item.id,
                quantity=item_input.quantity,
                price_at_order=menu_item.price
            )
            db.add(order_item)
            total_amount += menu_item.price * item_input.quantity
            
        new_order.total_amount = total_amount
        
        customer = db.query(models.Customer).filter(models.Customer.id == input.customer_id).first()
        if customer:
            customer.loyalty_points = (customer.loyalty_points or 0) + int(total_amount / 10)
            
        db.commit()
        db.refresh(new_order)
        return CreateOrderPayload(order=new_order)


class UpdateOrderStatusInput(graphene.InputObjectType):
    order_id = graphene.Int(required=True)
    status = graphene.String(required=True)

class UpdateOrderStatusPayload(graphene.ObjectType):
    order = graphene.Field(OrderType)

class UpdateOrderStatus(graphene.Mutation):
    class Arguments:
        input = UpdateOrderStatusInput(required=True)

    Output = UpdateOrderStatusPayload

    def mutate(self, info, input):
        db = get_db(info)
        order = db.query(models.Order).filter(models.Order.id == input.order_id).first()
        if not order:
            raise Exception("Order not found")
            
        valid_statuses = ["pending", "preparing", "ready", "served", "paid"]
        if input.status not in valid_statuses:
            raise Exception(f"Invalid status: {input.status}")
            
        order.status = input.status
        db.commit()
        db.refresh(order)
        return UpdateOrderStatusPayload(order=order)


class Mutation(graphene.ObjectType):
    createOrder = CreateOrder.Field()
    updateOrderStatus = UpdateOrderStatus.Field()

class Query(graphene.ObjectType):
    categories = graphene.List(CategoryType)
    orders = graphene.List(OrderType, status=graphene.String(default_value=None))
    customer = graphene.Field(CustomerType, id=graphene.Int(required=True))
    
    def resolve_categories(self, info):
        db = get_db(info)
        return db.query(models.Category).all()
        
    def resolve_orders(self, info, status=None):
        db = get_db(info)
        query = db.query(models.Order)
        if status:
            query = query.filter(models.Order.status == status)
        return query.all()
        
    def resolve_customer(self, info, id):
        db = get_db(info)
        return db.query(models.Customer).filter(models.Customer.id == id).first()

schema = graphene.Schema(query=Query, mutation=Mutation)
