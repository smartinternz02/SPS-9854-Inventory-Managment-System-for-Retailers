import os
import json
import sqlite3
import flask
from flask import Flask, url_for, request, redirect,render_template,flash
from flask import render_template as render
from flask import session
import re
DATABASE_NAME = 'inventory.sqlite'
app = Flask(__name__)
app.config.from_mapping(
    SECRET_KEY='inventory',
    DATABASE=os.path.join(app.instance_path, 'database', DATABASE_NAME),
)
link = {x: x for x in ["summary","location", "product", "movement", "logout"]}
link["index"] = '/summary'
def init_database():
    db = sqlite3.connect(DATABASE_NAME)
    cursor = db.cursor()


    cursor.execute("""
    CREATE TABLE IF NOT EXISTS products(prod_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    prod_name TEXT UNIQUE NOT NULL,
                    prod_quantity INTEGER NOT NULL,
                    unallocated_quantity INTEGER);
    """)
    cursor.execute("""
    CREATE TRIGGER IF NOT EXISTS default_prod_qty_to_unalloc_qty
                    AFTER INSERT ON products
                    FOR EACH ROW
                    WHEN NEW.unallocated_quantity IS NULL
                    BEGIN 
                        UPDATE products SET unallocated_quantity  = NEW.prod_quantity WHERE rowid = NEW.rowid;
                    END;

    """)

    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS location(loc_id INTEGER PRIMARY KEY AUTOINCREMENT,
                                 loc_name TEXT UNIQUE NOT NULL);
    """)


    cursor.execute("""
    CREATE TABLE IF NOT EXISTS logistics(trans_id INTEGER PRIMARY KEY AUTOINCREMENT,
                                prod_id INTEGER NOT NULL,
                                from_loc_id INTEGER NULL,
                                to_loc_id INTEGER NULL,
                                prod_quantity INTEGER NOT NULL,
                                trans_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                                FOREIGN KEY(prod_id) REFERENCES products(prod_id),
                                FOREIGN KEY(from_loc_id) REFERENCES location(loc_id),
                                FOREIGN KEY(to_loc_id) REFERENCES location(loc_id));
    """)
    db.commit()

@app.route("/")

    
@app.route("/login", methods =['GET', 'POST'])
def login():
    msg = ''
    if request.method == 'POST' :
        name = request.form['name']
        password = request.form['password']
        db = sqlite3.connect(DATABASE_NAME)
        cursor = db.cursor()
        cursor.execute('SELECT * FROM Users WHERE name = ? AND password = ?',(name, password ))
        account = cursor.fetchone()
        print (account)
        if (account):
            session['loggedin'] = True
            session['id'] = account[0]
            session['name'] = account[1]
            return render_template('home.html',link=link)
        else:
            msg = 'Incorrect username / password !'
            return msg
    return render_template('login.html')
@app.route('/home')        
def home():
    return render_template('home.html')             
    
@app.route('/register', methods =['GET', 'POST'])
def register():
    msg = ''
    if request.method == 'POST' :
        name = request.form['name']
        businesstype = request.form['businesstype']
        phone = request.form['phone']
        address = request.form['address']
        city = request.form['city']
        state = request.form['state']
        country = request.form['country']   
        email = request.form['email']
        password = request.form['password']
        db = sqlite3.connect(DATABASE_NAME)
        cursor = db.cursor()
        cursor.execute('SELECT * FROM Users WHERE name = ? AND password = ?',(name, password ))
        account = cursor.fetchone()
        if account: 
            msg = 'Account already exists !'
        
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            msg = 'Invalid email address !'
        elif not re.match(r'[A-Za-z0-9]+', name):
            msg = 'name must contain only characters and numbers !'
        else:
            cursor.execute('INSERT INTO Users VALUES (NULL,?,?,?,?,?,?,?,?,?)', (name,businesstype,phone,address,city,state,country,email,password ))
            db.commit()
            msg = 'You have successfully registered !'
            return redirect(url_for('login'))
    elif request.method == 'POST':
        msg = 'Please fill out the form !'
    return render_template('register.html', msg = msg)
   
@app.route('/logout')
def logout():
    
   session.pop('loggedin', None)
   session.pop('id', None)
   session.pop('username', None)
   return redirect(url_for('login'))

@app.route('/summary')
def summary():
    init_database()
    msg = None
    q_data, warehouse, products = None, None, None
    db = sqlite3.connect(DATABASE_NAME)
    cursor = db.cursor()
    try:
        cursor.execute("SELECT * FROM location")  
        warehouse = cursor.fetchall()
        cursor.execute("SELECT * FROM products")
        products = cursor.fetchall()
        cursor.execute("""
        SELECT prod_name, unallocated_quantity, prod_quantity FROM products
        """)
        q_data = cursor.fetchall()
    except sqlite3.Error as e:
        msg = f"An error occurred: {e.args[0]}"
    if msg:
        print(msg)

    return render('index.html', link=link, title="Summary", warehouses=warehouse, products=products, database=q_data)


@app.route('/product', methods=['POST', 'GET'])
def product():
    init_database()
    msg = None
    db = sqlite3.connect(DATABASE_NAME)
    cursor = db.cursor()

    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()

    if request.method == 'POST':
        prod_name = request.form['prod_name']
        quantity = request.form['prod_quantity']

        transaction_allowed = False
        if prod_name not in ['', ' ', None]:
            if quantity not in ['', ' ', None]:
                transaction_allowed = True

        if transaction_allowed:
            try:
                cursor.execute("INSERT INTO products (prod_name, prod_quantity) VALUES (?, ?)", (prod_name, quantity))
                db.commit()
            except sqlite3.Error as e:
                msg = f"An error occurred: {e.args[0]}"
            else:
                msg = f"{prod_name} added successfully"

            if msg:
                print(msg)

            return redirect(url_for('product'))

    return render('product.html',
                  link=link, products=products, transaction_message=msg,
                  title="Products Log")


@app.route('/location', methods=['POST', 'GET'])
def location():
    init_database()
    msg = None
    db = sqlite3.connect(DATABASE_NAME)
    cursor = db.cursor()

    cursor.execute("SELECT * FROM location")
    warehouse_data = cursor.fetchall()

    if request.method == 'POST':
        warehouse_name = request.form['warehouse_name']

        transaction_allowed = False
        if warehouse_name not in ['', ' ', None]:
            transaction_allowed = True

        if transaction_allowed:
            try:
                cursor.execute("INSERT INTO location (loc_name) VALUES (?)", (warehouse_name,))
                db.commit()
            except sqlite3.Error as e:
                msg = f"An error occurred: {e.args[0]}"
            else:
                msg = f"{warehouse_name} added successfully"

            if msg:
                print(msg)

            return redirect(url_for('location'))

    return render('location.html',
                  link=link, warehouses=warehouse_data, transaction_message=msg,
                  title="Warehouse Locations")


@app.route('/movement', methods=['POST', 'GET'])
def movement():
    init_database()
    msg = None
    db = sqlite3.connect(DATABASE_NAME)
    cursor = db.cursor()

    cursor.execute("SELECT * FROM logistics")
    logistics_data = cursor.fetchall()

    
    cursor.execute("SELECT prod_id, prod_name, unallocated_quantity FROM products")
    products = cursor.fetchall()

    cursor.execute("SELECT loc_id, loc_name FROM location")
    locations = cursor.fetchall()

    log_summary = []
    for p_id in [x[0] for x in products]:
        cursor.execute("SELECT prod_name FROM products WHERE prod_id = ?", (p_id, ))
        temp_prod_name = cursor.fetchone()

        for l_id in [x[0] for x in locations]:
            cursor.execute("SELECT loc_name FROM location WHERE loc_id = ?", (l_id,))
            temp_loc_name = cursor.fetchone()

            cursor.execute("""
            SELECT SUM(log.prod_quantity)
            FROM logistics log
            WHERE log.prod_id = ? AND log.to_loc_id = ?
            """, (p_id, l_id))
            sum_to_loc = cursor.fetchone()

            cursor.execute("""
            SELECT SUM(log.prod_quantity)
            FROM logistics log
            WHERE log.prod_id = ? AND log.from_loc_id = ?
            """, (p_id, l_id))
            sum_from_loc = cursor.fetchone()

            if sum_from_loc[0] is None:
                sum_from_loc = (0,)
            if sum_to_loc[0] is None:
                sum_to_loc = (0,)

            log_summary += [(temp_prod_name + temp_loc_name + (sum_to_loc[0] - sum_from_loc[0],))]

  
    alloc_json = {}
    for row in log_summary:
        try:
            if row[1] in alloc_json[row[0]].keys():
                alloc_json[row[0]][row[1]] += row[2]
            else:
                alloc_json[row[0]][row[1]] = row[2]
        except (KeyError, TypeError):
            alloc_json[row[0]] = {}
            alloc_json[row[0]][row[1]] = row[2]
    alloc_json = json.dumps(alloc_json)

    if request.method == 'POST':
        
        prod_name = request.form['prod_name']
        from_loc = request.form['from_loc']
        to_loc = request.form['to_loc']
        quantity = request.form['quantity']

       
        if from_loc in [None, '', ' ']:
            try:
                cursor.execute("""
                    INSERT INTO logistics (prod_id, to_loc_id, prod_quantity) 
                    SELECT products.prod_id, location.loc_id, ? 
                    FROM products, location 
                    WHERE products.prod_name == ? AND location.loc_name == ?
                """, (quantity, prod_name, to_loc))

               
                cursor.execute("""
                UPDATE products 
                SET unallocated_quantity = unallocated_quantity - ? 
                WHERE prod_name == ?
                """, (quantity, prod_name))
                db.commit()

            except sqlite3.Error as e:
                msg = f"An error occurred: {e.args[0]}"
            else:
                msg = "Transaction added successfully"

        elif to_loc in [None, '', ' ']:
            print("To Location wasn't specified, will be unallocated")
            try:
                cursor.execute("""
                INSERT INTO logistics (prod_id, from_loc_id, prod_quantity) 
                SELECT products.prod_id, location.loc_id, ? 
                FROM products, location 
                WHERE products.prod_name == ? AND location.loc_name == ?
                """, (quantity, prod_name, from_loc))

              
                cursor.execute("""
                UPDATE products 
                SET unallocated_quantity = unallocated_quantity + ? 
                WHERE prod_name == ?
                """, (quantity, prod_name))
                db.commit()

            except sqlite3.Error as e:
                msg = f"An error occurred: {e.args[0]}"
            else:
                msg = "Transaction added successfully"


        else:
            try:
                cursor.execute("SELECT loc_id FROM location WHERE loc_name == ?", (from_loc,))
                from_loc = ''.join([str(x[0]) for x in cursor.fetchall()])

                cursor.execute("SELECT loc_id FROM location WHERE loc_name == ?", (to_loc,))
                to_loc = ''.join([str(x[0]) for x in cursor.fetchall()])

                cursor.execute("SELECT prod_id FROM products WHERE prod_name == ?", (prod_name,))
                prod_id = ''.join([str(x[0]) for x in cursor.fetchall()])

                cursor.execute("""
                INSERT INTO logistics (prod_id, from_loc_id, to_loc_id, prod_quantity)
                VALUES (?, ?, ?, ?)
                """, (prod_id, from_loc, to_loc, quantity))
                db.commit()

            except sqlite3.Error as e:
                msg = f"An error occurred: {e.args[0]}"
            else:
                msg = "Transaction added successfully"

        
        if msg:
            print(msg)
            return redirect(url_for('movement'))

    return render('movement.html', title="ProductMovement",
                  link=link, trans_message=msg,
                  products=products, locations=locations, allocated=alloc_json,
                  logs=logistics_data, database=log_summary)


@app.route('/delete')
def delete():
    type_ = request.args.get('type')
    db = sqlite3.connect(DATABASE_NAME)
    cursor = db.cursor()

    if type_ == 'location':
        id_ = request.args.get('loc_id')

        cursor.execute("SELECT prod_id, SUM(prod_quantity) FROM logistics WHERE to_loc_id = ? GROUP BY prod_id", (id_,))
        in_place = cursor.fetchall()

        cursor.execute("SELECT prod_id, SUM(prod_quantity) FROM logistics WHERE from_loc_id = ? GROUP BY prod_id", (id_,))
        out_place = cursor.fetchall()

        
        in_place = dict(in_place)
        out_place = dict(out_place)

       
        all_place = {}
        for x in in_place.keys():
            if x in out_place.keys():
                all_place[x] = in_place[x] - out_place[x]
            else:
                all_place[x] = in_place[x]
       

        for products_ in all_place.keys():
            cursor.execute("""
            UPDATE products SET unallocated_quantity = unallocated_quantity + ? WHERE prod_id = ?
            """, (all_place[products_], products_))

        cursor.execute("DELETE FROM location WHERE loc_id == ?", str(id_))
        db.commit()

        return redirect(url_for('location'))

    elif type_ == 'product':
        id_ = request.args.get('prod_id')
        cursor.execute("DELETE FROM products WHERE prod_id == ?", str(id_))
        db.commit()

        return redirect(url_for('product'))


@app.route('/edit', methods=['POST', 'GET'])
def edit():
    type_ = request.args.get('type')
    db = sqlite3.connect(DATABASE_NAME)
    cursor = db.cursor()

    if type_ == 'location' and request.method == 'POST':
        loc_id = request.form['loc_id']
        loc_name = request.form['loc_name']

        if loc_name:
            cursor.execute("UPDATE location SET loc_name = ? WHERE loc_id == ?", (loc_name, str(loc_id)))
            db.commit()

        return redirect(url_for('location'))

    elif type_ == 'product' and request.method == 'POST':
        prod_id = request.form['prod_id']
        prod_name = request.form['prod_name']
        prod_quantity = request.form['prod_quantity']

        if prod_name:
            cursor.execute("UPDATE products SET prod_name = ? WHERE prod_id == ?", (prod_name, str(prod_id)))
        if prod_quantity:
            cursor.execute("SELECT prod_quantity FROM products WHERE prod_id = ?", (prod_id,))
            old_prod_quantity = cursor.fetchone()[0]
            cursor.execute("UPDATE products SET prod_quantity = ?, unallocated_quantity =  unallocated_quantity + ? - ?"
                           "WHERE prod_id == ?", (prod_quantity, prod_quantity, old_prod_quantity, str(prod_id)))
        db.commit()

        return redirect(url_for('product'))

    return render(url_for(type_))
if __name__=='__main__':
    app.run(host='0.0.0.0',debug=True,port=2000)