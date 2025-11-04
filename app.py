from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta


app = Flask(__name__, template_folder="./templates")
CORS(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///library.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    author = db.Column(db.String(100))
    total_copies = db.Column(db.Integer, default=1)
    available_copies = db.Column(db.Integer, default=1)


class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    national_id = db.Column(db.String(10), unique=True, nullable=False)
    email = db.Column(db.String(120))


class Loan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    loan_date = db.Column(db.DateTime, default=datetime.utcnow)
    due_date = db.Column(db.DateTime)
    return_date = db.Column(db.DateTime)
    book = db.relationship('Book', backref='loans')
    student = db.relationship('Student', backref='loans')


@app.route('/')
def index():
    return render_template('library.html')


@app.route('/api/books/add', methods=['POST'])
def add_book():
    data = request.json
    title = data.get('title')
    author = data.get('author')
    total_copies = data.get('total_copies', 1)
    available_copies = data.get('available_copies', total_copies)
    if not title:
        return jsonify({'error': 'Title is required'}), 400
    book = Book(title=title, author=author, total_copies=total_copies, available_copies=available_copies)
    db.session.add(book)
    db.session.commit()
    return jsonify({'message': 'Book added successfully'}), 201


@app.route('/api/books/delete/<int:book_id>', methods=['DELETE'])
def delete_book(book_id):
    book = Book.query.get(book_id)
    if not book:
        return jsonify({'error': 'Book not found'}), 404
    active_loans = Loan.query.filter_by(book_id=book_id, return_date=None).count()
    if active_loans > 0:
        return jsonify({'error': 'Book has active loans'}), 400
    db.session.delete(book)
    db.session.commit()
    return jsonify({'message': 'Book deleted'}), 200


@app.route('/api/books/list', methods=['GET'])
def list_books():
    books = Book.query.all()
    result = [{'id': b.id, 'title': b.title, 'author': b.author, 'total_copies': b.total_copies, 'available_copies': b.available_copies} for b in books]
    return jsonify(result), 200


@app.route('/api/students/add', methods=['POST'])
def add_student():
    data = request.json
    name = data.get('name')
    national_id = data.get('national_id')
    email = data.get('email')
    if not name or not national_id:
        return jsonify({'error': 'Name and National ID required'}), 400
    try:
        student = Student(name=name, national_id=national_id, email=email)
        db.session.add(student)
        db.session.commit()
        return jsonify({'message': 'Student added successfully'}), 201
    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'National ID must be unique'}), 400


@app.route('/api/students/delete/<int:student_id>', methods=['DELETE'])
def delete_student(student_id):
    student = Student.query.get(student_id)
    if not student:
        return jsonify({'error': 'Student not found'}), 404
    active_loans = Loan.query.filter_by(student_id=student_id, return_date=None).count()
    if active_loans > 0:
        return jsonify({'error': 'Student has active loans'}), 400
    db.session.delete(student)
    db.session.commit()
    return jsonify({'message': 'Student deleted'}), 200


@app.route('/api/students/list', methods=['GET'])
def list_students():
    students = Student.query.all()
    result = [{'id': s.id, 'name': s.name, 'national_id': s.national_id, 'email': s.email} for s in students]
    return jsonify(result), 200


@app.route('/api/loans/add', methods=['POST'])
def add_loan():
    data = request.json
    book_id = data.get('book_id')
    student_id = data.get('student_id')
    book = Book.query.get(book_id)
    student = Student.query.get(student_id)
    if not book or not student:
        return jsonify({'error': 'Book or Student not found'}), 404
    if book.available_copies < 1:
        return jsonify({'error': 'Book not available'}), 400
    due_date = datetime.utcnow() + timedelta(days=14)
    book.available_copies -= 1
    loan = Loan(book_id=book_id, student_id=student_id, due_date=due_date)
    db.session.add(loan)
    db.session.commit()
    return jsonify({
        'message': 'Loan recorded successfully',
        'loan': {
            'id': loan.id,
            'book_id': loan.book_id,
            'student_id': loan.student_id,
            'borrow_date': loan.loan_date.isoformat(),
            'due_date': loan.due_date.isoformat()
        }
    }), 201


@app.route('/api/loans/return/<int:loan_id>', methods=['PUT'])
def return_book(loan_id):
    loan = Loan.query.get(loan_id)
    if not loan or loan.return_date:
        return jsonify({'error': 'Invalid loan ID or already returned'}), 400
    loan.return_date = datetime.utcnow()
    loan.book.available_copies += 1
    db.session.commit()
    return jsonify({'message': 'Book returned successfully'}), 200


@app.route('/api/loans/list', methods=['GET'])
def list_loans():
    loans = Loan.query.filter_by(return_date=None).all()
    result = []
    for l in loans:
        result.append({
            'id': l.id,
            'book_id': l.book_id,
            'student_id': l.student_id,
            'book_title': l.book.title,
            'student_name': l.student.name,
            'borrow_date': l.loan_date.isoformat() if l.loan_date else None,
            'due_date': l.due_date.isoformat() if l.due_date else None,
            'returned': False
        })
    return jsonify(result), 200


with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
