from flask import Flask, render_template, request, redirect, url_for, session
from flask_session import Session  # Add this import
import csv
import random
import requests
from pathlib import Path

app = Flask(__name__)

# Configure server-side session storage
app.config['SESSION_TYPE'] = 'filesystem'  # Use filesystem to store sessions
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
app.secret_key = 'supersecretkey'
Session(app)  # Initialize the session extension
app.secret_key = 'supersecretkey'

# Utility functions
def load_questions(file_paths):
    """Load questions from one or more CSV files."""
    all_questions = []
    for file_path in file_paths:
        try:
            with open(file_path, 'r') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    all_questions.append(row)
        except FileNotFoundError:
            print(f"File {file_path} not found!")
            continue
    return all_questions

@app.route('/')
def main_menu():
    return render_template('main_menu.html')


@app.route('/unit/<int:unit_id>')
def load_unit(unit_id):
    """Load questions for the selected unit."""
    global questions

    # Map unit numbers to names
    unit_names = {
        1: "Food Technology",
        2: "Dairy Technology",
        3: "Veterinary Sciences",
        4: "Nutritional Biochemistry and Food Analysis",
        5: "Microbiological, Biotechnological and Medical Aspects",
        6: "All Units"
    }

    # Define Drive URLs
    drive_urls = {
        1: ["https://drive.google.com/uc?id=1I5g1_6K1KMzEU7Gzjp2FcQT24m2zeSK9&export=download"],
        2: ["https://drive.google.com/uc?id=1JkM-OI8xueFlf2AJLkIrzT4JNPEHWtWa&export=download"],
        3: ["https://drive.google.com/uc?id=15d_HjVX6C5I18uWWlhJ0a2T03osP6SrX&export=download"],
        4: ["https://drive.google.com/uc?id=1bj12gLuzuII-MrD6tGKLo8b-3_lxB3n1&export=download"],
        5: ["https://drive.google.com/uc?id=1j8ecIIBsfKQwr7QMd1s3tYHL7PxZwCEA&export=download"],
        6: [
            "https://drive.google.com/uc?id=1I5g1_6K1KMzEU7Gzjp2FcQT24m2zeSK9&export=download",
            "https://drive.google.com/uc?id=1JkM-OI8xueFlf2AJLkIrzT4JNPEHWtWa&export=download",
            "https://drive.google.com/uc?id=15d_HjVX6C5I18uWWlhJ0a2T03osP6SrX&export=download",
            "https://drive.google.com/uc?id=1bj12gLuzuII-MrD6tGKLo8b-3_lxB3n1&export=download",
            "https://drive.google.com/uc?id=1j8ecIIBsfKQwr7QMd1s3tYHL7PxZwCEA&export=download"
        ],
    }

    file_urls = drive_urls.get(unit_id, [])
    downloaded_files = []
    for url in file_urls:
        try:
            file_path = Path(f"temp_unit_{unit_id}.csv")
            with open(file_path, 'wb') as file:
                file.write(requests.get(url).content)
            downloaded_files.append(file_path)
        except Exception as e:
            print(f"Error downloading file: {e}")
            return redirect(url_for('main_menu'))

    questions = load_questions(downloaded_files)

    # Make sure to only unlink files if they exist
    for file in downloaded_files:
        if file.exists():
            file.unlink()  # Clean up temporary files

    if not questions:
        return "No questions available."

    session['unit_name'] = unit_names.get(unit_id, "Unknown Unit")
    session['unit_id'] = unit_id  # Store unit_id in session for quiz flow
    return redirect(url_for('select_question_count'))



@app.route('/select_count', methods=['GET', 'POST'])
def select_question_count():
    """Prompt the user to select the number of questions."""
    global questions  # Ensure you use the questions loaded in the previous route

    if request.method == 'POST':
        try:
            num_questions = int(request.form['num_questions'])
            if num_questions < 1 or num_questions > len(questions):
                raise ValueError
            # Now we sample the actual questions instead of just 'ID'
            session['selected_questions'] = random.sample(questions, num_questions)
            session['score'] = 0
            session['current_question_index'] = 0
            return redirect(url_for('quiz'))
        except ValueError:
            return "Invalid number of questions!"

    # Pass the max_questions dynamically based on the number of questions available
    return render_template('select_count.html', max_questions=len(questions))



@app.route('/quiz', methods=['GET', 'POST'])
def quiz():
    """Display the quiz screen with immediate feedback and quit option."""
    feedback = None  # Initialize feedback

    # Check if selected questions exist in the session
    if 'selected_questions' not in session:
        print("Error: selected_questions not found in session.")  # Debugging log
        return redirect(url_for('main_menu'))

    current_index = session.get('current_question_index', 0)
    question = session['selected_questions'][current_index]
    options = {
        'A': question.get('Option_A', ''),
        'B': question.get('Option_B', ''),
        'C': question.get('Option_C', ''),
        'D': question.get('Option_D', '')
    }

    if request.method == 'POST':
        action = request.form.get('action', '')

        if action == 'submit':
            # Handle answer submission
            selected_answer = request.form.get('answer', '').strip().upper()
            correct_answer = question['Correct_Answer'].strip().upper()

            feedback = {
                'selected': selected_answer,
                'correct_answer': correct_answer,
                'is_correct': selected_answer == correct_answer
            }

            if feedback['is_correct']:
                session['score'] += 1

        elif action == 'next':
            # Move to the next question
            session['current_question_index'] += 1
            if session['current_question_index'] >= len(session['selected_questions']):
                return redirect(url_for('quiz_end'))
            return redirect(url_for('quiz'))

        elif action == 'quit':
            # Handle quiz quitting
            session.pop('selected_questions', None)
            session.pop('current_question_index', None)
            session.pop('score', None)
            return redirect(url_for('main_menu'))

    return render_template(
        'quiz.html',
        question=question,
        options=options,
        index=current_index + 1,
        total=len(session['selected_questions']),
        score=session['score'],
        feedback=feedback
    )


@app.route('/quiz_end')
def quiz_end():
    """Display the final score."""
    return render_template('quiz_end.html', score=session['score'], total=len(session['selected_questions']))


if __name__ == '__main__':
    app.run(debug=True)
