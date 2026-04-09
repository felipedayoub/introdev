from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session, select

from database import create_db_and_tables, get_session, engine
from models import User, Product, CartItem

# --- Sessão simples via cookie (didático, NÃO seguro para produção) ---
# guardamos apenas o username no cookie

COOKIE_NAME = "user"

# helper para obter usuário atual a partir do cookie
from fastapi import Response

def get_current_user(request: Request, session: Session):
    username = request.cookies.get(COOKIE_NAME)
    if not username:
        return None
    return session.exec(select(User).where(User.username == username)).first()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # STARTUP
    create_db_and_tables()

    with Session(engine) as session:
        if not session.exec(select(Product)).first():
            products = [
                Product(name="Camiseta", price=50, file_name="/static/tshirt.jpg"),
                Product(name="Calça", price=120, file_name="/static/pants.jpg"),
                Product(name="Jaqueta", price=200, file_name="/static/jacket.jpg"),
            ]
            session.add_all(products)
            session.commit()

    yield

    # SHUTDOWN (opcional)

app = FastAPI(lifespan=lifespan)
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# ---------- LOGIN ----------
@app.post("/login")
def login(request: Request, response: Response, username: str = Form(...), session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.username == username)).first()
    if not user:
        user = User(username=username)
        session.add(user)
        session.commit()
        session.refresh(user)

    # salva no cookie
    response.set_cookie(key=COOKIE_NAME, value=user.username)
    return f"Logado como {user.username}"

@app.post("/logout")
def logout(response: Response):
    response.delete_cookie(key=COOKIE_NAME)
    return "Deslogado"


# ---------- PÁGINAS ----------
@app.get("/", response_class=HTMLResponse)
def index(request: Request, session: Session = Depends(get_session)):
    user = get_current_user(request, session)
    return templates.TemplateResponse("index.html", {"request": request, "user": user})

@app.get("/catalog", response_class=HTMLResponse)
def catalog(request: Request, session: Session = Depends(get_session)):
    products = session.exec(select(Product)).all()
    user = get_current_user(request, session)
    return templates.TemplateResponse("catalog.html", {"request": request, "products": products, "user": user})

@app.get("/cart", response_class=HTMLResponse)
def cart(request: Request, session: Session = Depends(get_session)):
    user = get_current_user(request, session)
    if not user:
        return HTMLResponse("Faça login primeiro")
    items = session.exec(select(CartItem).where(CartItem.user_id == user.id)).all()
    return templates.TemplateResponse("cart.html", {"request": request, "items": items})

# ---------- CRUD HTMX ----------
@app.post("/cart")
def add_to_cart(request: Request, product_id: int = Form(...), session: Session = Depends(get_session)):
    user = get_current_user(request, session)
    if not user:
        return "Faça login primeiro!"
    item = CartItem(user_id=user.id, product_id=product_id)
    session.add(item)
    session.commit()
    return "Adicionado!"

@app.delete("/cart/{item_id}")
def delete_item(item_id: int, session: Session = Depends(get_session)):
    item = session.get(CartItem, item_id)
    if item:
        session.delete(item)
        session.commit()
    return "Removido"

# limpar toda a sacola
@app.delete("/cart")
def clear_cart(request: Request, session: Session = Depends(get_session)):
    user = get_current_user(request, session)
    if not user:
        return "NOT_LOGGED"

    items = session.exec(select(CartItem).where(CartItem.user_id == user.id)).all()
    for item in items:
        session.delete(item)
    session.commit()

    return "Carrinho limpo"


