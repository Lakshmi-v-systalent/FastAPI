from fastapi import FastAPI,HTTPException
from models import TodoItem,TodoItemResponse,UpdateTodoItem
import sqlite3
from typing import List

app=FastAPI()

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
        description TEXT
    )
    ''')
    conn.commit()
    conn.close()
    
create_table()


#API
@app.post('/todos', response_model=TodoItemResponse)
def create_todo_item(item: TodoItem):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO todos (title, description) VALUES (?, ?)', (item.title, item.description))
    conn.commit()
    item_id = cursor.lastrowid
    conn.close()
    return TodoItemResponse(id=item_id, title=item.title, description=item.description)

@app.get('/todos', response_model=List[TodoItemResponse])
def read_todo_items():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM todos')
    rows = cursor.fetchall()
    conn.close()
    return [TodoItemResponse(id=row['id'], title=row['title'], description=row['description']) for row in rows]
@app.get('/todos/{todo_id}', response_model=TodoItemResponse)
def read_todo_item(todo_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM todos WHERE id = ?', (todo_id,))
    row = cursor.fetchone()
    conn.close()
    if row is None:
        raise HTTPException(status_code=404, detail="Todo item not found")
    return dict(row)    
    
@app.patch('/todos/{todo_id}', response_model=TodoItemResponse)
def update_todo_item(todo_id: int, item: UpdateTodoItem):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM todos WHERE id = ?', (todo_id,))
    existing_item = cursor.fetchone()
    if existing_item is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Todo item not found")
    
    
    updated_data = item.model_dump(exclude_unset=True)
    
    updated_title = updated_data.get("title", existing_item["title"])
    updated_description = updated_data.get("description", existing_item["description"])
    
   
    cursor.execute('UPDATE todos SET title = ?, description = ? WHERE id = ?', 
                   (updated_title, updated_description, todo_id))
    conn.commit()
    conn.close()
    return {**updated_data, 'id': todo_id}
@app.delete('/todos/{todo_id}', response_model=dict)
def delete_todo_item(todo_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM todos WHERE id = ?', (todo_id,))
    existing_item = cursor.fetchone()
    if existing_item is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Todo item not found")
    
    cursor.execute('DELETE FROM todos WHERE id = ?', (todo_id,))
    conn.commit()
    conn.close()
    return {"message": "Todo item deleted successfully"}
