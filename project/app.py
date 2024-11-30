from flask import Flask, render_template, request, redirect, url_for, session
import mysql.connector
from mysql.connector import Error

app = Flask(__name__, template_folder="templates")
app.secret_key = 'your_secret_key'

# MySQL 데이터베이스 연결
def get_db_connection():    
    try:
        return mysql.connector.connect(
            host="127.0.0.1",
            port=3306,
            user="root",
            password="1234",
            database="dbproject"
        )
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_id = request.form['id']
        password = request.form['password']

        try:
            connection = get_db_connection()
            if not connection:
                return render_template('login.html', error="Database connection failed.")
            
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT * FROM member WHERE id = %s AND password = %s", (user_id, password))
            user = cursor.fetchone()
            connection.close()

            if user:
                session['user_id'] = user['id']
                session['name'] = user['name']
                return redirect(url_for('reviews'))
            else:
                return render_template('login.html', error="Invalid ID or password")
        except Error as e:
            print(f"Error during login: {e}")
            return render_template('login.html', error="Login failed. Please try again.")
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        user_id = request.form['id']
        password = request.form['password']
        name = request.form['name']
        age = request.form['age']

        try:
            connection = get_db_connection()
            if not connection:
                return render_template('register.html', error="Database connection failed.")
            
            cursor = connection.cursor()
            cursor.execute("INSERT INTO member (id, password, name, age) VALUES (%s, %s, %s, %s)", (user_id, password, name, age))
            connection.commit()
            connection.close()
            return redirect(url_for('login'))
        except Error as e:
            print(f"Error during registration: {e}")
            return render_template('register.html', error="Registration failed. Please try again.")
    return render_template('register.html')

@app.route('/reviews', methods=['GET', 'POST'])
def reviews():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    connection = get_db_connection()
    if not connection:
        return "Database connection failed.", 500

    cursor = connection.cursor(dictionary=True)

    # 강의 목록 조회
    cursor.execute("SELECT * FROM lecture")
    lectures = cursor.fetchall()

    # 리뷰 등록
    if request.method == 'POST':
        if 'lecture_id' not in request.form or 'rating' not in request.form or 'content' not in request.form:
            return "Missing required fields", 400

        lecture_id = request.form['lecture_id']
        title = ""  # Title field removed
        content = request.form['content']
        rating = request.form['rating']
        user_id = session['user_id']

        try:
            cursor.execute("""
                INSERT INTO lecture_review (lecture_id, member_id, title, content, rating)
                VALUES (%s, %s, %s, %s, %s)
            """, (lecture_id, user_id, title, content, rating))
            connection.commit()
        except Error as e:
            print(f"Error saving review: {e}")
            connection.close()
            return render_template('reviews.html', error="Failed to save review.", lectures=lectures)

    # 모든 리뷰 목록 조회 (id 필드를 포함하여 가져옴)
    cursor.execute("""
        SELECT r.id, r.title, r.content, r.rating, m.name, l.name AS lecture_name, l.professor
        FROM lecture_review r
        INNER JOIN member m ON r.member_id = m.id
        INNER JOIN lecture l ON r.lecture_id = l.id
    """)
    reviews = cursor.fetchall()
    connection.close()

    return render_template('reviews.html', reviews=reviews, lectures=lectures)

@app.route('/rate')
def rate():
    connection = get_db_connection()
    if not connection:
        return "Database connection failed.", 500

    cursor = connection.cursor(dictionary=True)

    try:
        # 강의별 평균 평점 및 교수 포함하여 조회
        cursor.execute("""
            SELECT 
                l.name AS lecture_name, 
                l.professor AS professor,
                COALESCE(AVG(r.rating), 0) AS average_rating,
                COUNT(r.id) AS review_count
            FROM lecture l
            LEFT JOIN lecture_review r ON l.id = r.lecture_id
            GROUP BY l.id, l.name, l.professor
            ORDER BY lecture_name
        """)
        lectures = cursor.fetchall()

        if not lectures:
            lectures = []
    except Error as e:
        print(f"Error fetching lecture ratings: {e}")
        lectures = []
    finally:
        connection.close()

    return render_template('rate.html', lectures=lectures)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/edit_review/<int:review_id>', methods=['GET', 'POST'])
def edit_review(review_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        rating = request.form['rating']

        try:
            cursor.execute("""
                UPDATE lecture_review
                SET title = %s, content = %s, rating = %s
                WHERE id = %s AND member_id = %s
            """, (title, content, rating, review_id, session['user_id']))
            connection.commit()
            connection.close()
            return redirect(url_for('reviews'))
        except Error as e:
            print(f"Error updating review: {e}")
            connection.close()
            return "Error updating review", 500

    cursor.execute("SELECT * FROM lecture_review WHERE id = %s AND member_id = %s", (review_id, session['user_id']))
    review = cursor.fetchone()
    connection.close()

    if review:
        return render_template('review_edit.html', review=review)
    else:
        return "Review not found or you don't have permission to edit it.", 404

@app.route('/delete_review/<int:review_id>', methods=['GET'])
def delete_review(review_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("DELETE FROM lecture_review WHERE id = %s AND member_id = %s", (review_id, session['user_id']))
        connection.commit()
        connection.close()
        return redirect(url_for('reviews'))
    except Error as e:
        print(f"Error deleting review: {e}")
        connection.close()
        return "Error deleting review", 500


if __name__ == '__main__':
    app.run(debug=True, port=8000)
