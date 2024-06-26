from datetime import datetime, timedelta, timezone
from fastapi import FastAPI,HTTPException,status,Depends
from jose import JWTError, jwt
#import logging
import secrets
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from models import TodoItem,TodoItemResponse,UpdateTodoItem, UserLogin, UserLoginResponse, UserRegistration, UserRegistrationResponse
import sqlite3
from typing import Annotated, List, Optional
from passlib.context import CryptContext

# Configure logging
#logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

app=FastAPI()
SECRET_KEY =secrets.token_urlsafe(32)
print(f'Secret key: {SECRET_KEY }')

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
# Database setup
def get_db_connection():
    conn = sqlite3.connect('todo.db')
    conn.row_factory = sqlite3.Row
    return conn
def create_table():
    conn=get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS todos (
        id INTEGER PRIMARY KEY,
        title TEXT NOT NULL,
        description TEXT,
        user_id INTEGER NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        username TEXT NOT NULL UNIQUE,
        hashed_password TEXT NOT NULL,
        email TEXT,
        full_name TEXT,
        disabled BOOLEAN NOT NULL CHECK (disabled IN (0, 1))
    )
    ''')
    conn.commit()
    conn.close()
    
create_table()


def get_password_hash(password):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_user(db, username: str):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    if row:
        return dict(row)
    return None

def authenticate_user(db, username: str, password: str):
    user = get_user(db, username)
    if not user:
        return False
    if not verify_password(password, user["hashed_password"]):
        return False
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
       expire = datetime.now(timezone.utc) + expires_delta

    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = {"username": username}
    except JWTError:
        raise credentials_exception
    conn = get_db_connection()
    user = get_user(conn, token_data["username"])
    conn.close()
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(
    current_user: Annotated[UserRegistrationResponse, Depends(get_current_user)]
):
    if current_user["disabled"]:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

@app.post("/register", response_model=UserRegistrationResponse,tags=["User Registration"])
async def register_user(user: UserRegistration):
    conn = get_db_connection()
    cursor = conn.cursor()
    hashed_password = get_password_hash(user.password)

    try:
        cursor.execute(
            'INSERT INTO users (username, hashed_password, email, full_name, disabled) VALUES (?, ?, ?, ?, ?)',
            (user.username, hashed_password, user.email, user.full_name, 0)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="Username already registered")

    conn.close()
    
    # Return the registered user's username
    return UserRegistrationResponse(username=user.username)


@app.get("/register{Userid}", response_model=UserRegistrationResponse,tags=["User Registration"])
async def get_register_user(Userid:int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT username, email, full_name, disabled FROM users WHERE id = ?', (Userid,))
    row = cursor.fetchone()
    
    conn.close()
    
    if row is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    user = UserRegistrationResponse(
        username=row[0],
        email=row[1],
        full_name=row[2],
        disabled=bool(row[3])
    )
    return user
'''@app.post("/login", response_model=UserLoginResponse, tags=["User Authentication"])
async def login_user(user: UserLogin):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT hashed_password FROM users WHERE username = ?', (user.username,))
    row = cursor.fetchone()
    
    if row is None:
        conn.close()
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    hashed_password = row[0]
    
    if not verify_password(user.password, hashed_password):
        conn.close()
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    conn.close()
    
    return UserLoginResponse(username=user.username, message="Login successful")'''


@app.post("/token", response_model=UserLoginResponse ,tags=["User Authentication"])
async def login_user(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT id, hashed_password FROM users WHERE username = ?', (form_data.username,))
    row = cursor.fetchone()
    
    if row is None:
        conn.close()
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    user_id, hashed_password = row
    
    if not verify_password(form_data.password, hashed_password):
        conn.close()
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    conn.close()
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": form_data.username, "user_id": user_id}, expires_delta=access_token_expires)
    
    return UserLoginResponse(
        username=form_data.username,
        access_token=access_token,
        token_type="bearer",
        message="auth token received"
    )

#API
@app.post('/todos', response_model=TodoItemResponse)
def create_todo_item(item: TodoItem, current_user: Annotated[UserRegistrationResponse, Depends(get_current_active_user)]):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO todos (title, description, user_id) VALUES (?, ?, ?)', (item.title, item.description, current_user['id']))
    conn.commit()
    item_id = cursor.lastrowid
    conn.close()
    return TodoItemResponse(id=item_id, title=item.title, description=item.description)

@app.get('/todos', response_model=List[TodoItemResponse])
def read_todo_items(current_user: Annotated[UserRegistrationResponse, Depends(get_current_active_user)]):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM todos WHERE user_id = ?', (current_user['id'],))
    rows = cursor.fetchall()
    conn.close()
    return [TodoItemResponse(id=row['id'], title=row['title'], description=row['description']) for row in rows]

@app.get('/todos/{todo_id}', response_model=TodoItemResponse)
def read_todo_item(todo_id: int, current_user: Annotated[UserRegistrationResponse, Depends(get_current_active_user)]):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM todos WHERE id = ? AND user_id = ?', (todo_id, current_user['id']))
    row = cursor.fetchone()
    conn.close()
    if row is None:
        raise HTTPException(status_code=404, detail="Todo item not found")
    return dict(row)

    
@app.patch('/todos/{todo_id}', response_model=TodoItemResponse)
def update_todo_item(todo_id: int, item: UpdateTodoItem, current_user: Annotated[UserRegistrationResponse, Depends(get_current_active_user)]):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM todos WHERE id = ? AND user_id = ?', (todo_id, current_user['id']))
    existing_item = cursor.fetchone()
    if existing_item is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Todo item not found")
    
    updated_data = item.model_dump(exclude_unset=True)
    updated_title = updated_data.get("title", existing_item["title"])
    updated_description = updated_data.get("description", existing_item["description"])
    
    cursor.execute('UPDATE todos SET title = ?, description = ? WHERE id = ? AND user_id = ?', 
                   (updated_title, updated_description, todo_id, current_user['id']))
    conn.commit()
    conn.close()
    return {**updated_data, 'id': todo_id}

@app.delete('/todos/{todo_id}', response_model=dict)
def delete_todo_item(todo_id: int, current_user: Annotated[UserRegistrationResponse, Depends(get_current_active_user)]):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM todos WHERE id = ? AND user_id = ?', (todo_id, current_user['id']))
    existing_item = cursor.fetchone()
    if existing_item is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Todo item not found")
    
    cursor.execute('DELETE FROM todos WHERE id = ? AND user_id = ?', (todo_id, current_user['id']))
    conn.commit()
    conn.close()
    return {"message": "Todo item deleted successfully"}

