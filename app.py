from flask import Flask, request, jsonify, render_template, send_from_directory
import requests
from werkzeug.utils import secure_filename
import os
import PyPDF2
import logging
from flask_cors import CORS
import json
import sqlite3
import random
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

app = Flask(__name__)

# Enable CORS for all routes
CORS(app)

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Define the system prompt
SYSTEM_PROMPT = "You are an AI assistant that generates questions from a given text. Do not include the starting 'here are the questions' in your output just give the questions. Also write the number of marks for the question (either 4 or 6 depending on the difficulty). The questions should be relevant, engaging, and cover the key topics in the text. Also make sure that there are 2 \n after each question"

# Set the upload folder
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Database setup
DATABASE = 'data/questions.db'

def init_db():
    os.makedirs('data', exist_ok=True)  # Ensure the data directory exists
    logging.debug("Data directory created or already exists.")
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def clear_questions():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM questions')  # Clear existing questions
    conn.commit()
    conn.close()

def store_questions(questions):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    for question in questions:
        cursor.execute('INSERT INTO questions (question) VALUES (?)', (question,))
    conn.commit()
    conn.close()

def get_randomized_questions():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT question FROM questions')
    questions = [row[0] for row in cursor.fetchall()]
    random.shuffle(questions)
    conn.close()
    return questions

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate-questions', methods=['POST'])
def generate_questions():
    try:
        logging.debug("Received request to generate questions.")
        
        # Get the base prompt and number of questions from the request
        base_prompt = request.form['base_prompt']
        num_questions = int(request.form['num_questions'])  # Get the number of questions
        logging.debug(f"Base prompt: {base_prompt}, Number of questions: {num_questions}")

        # Get the uploaded syllabus file
        syllabus_file = request.files['syllabus']
        logging.debug(f"Uploaded file: {syllabus_file.filename}")

        # Save the uploaded file
        filename = secure_filename(syllabus_file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        syllabus_file.save(filepath)
        logging.debug(f"Saved file to: {filepath}")

        # Extract text from the PDF file
        syllabus_text = extract_text_from_pdf(filepath)
        logging.debug(f"Extracted syllabus text: {syllabus_text[:100]}")  # Log the first 100 characters

        # Combine the system prompt, user prompt, and syllabus text
        prompt = f"{SYSTEM_PROMPT}\n\nBase prompt: {base_prompt}\n\nText: {syllabus_text}\n\nGenerate {num_questions} questions."
        logging.debug(f"Sending prompt to Ollama API: {prompt}")

        # Make a request to the Ollama API with streaming enabled
        response = requests.post(
            'http://localhost:11434/api/generate',
            json={"model": "llama3.1", "prompt": prompt},
            stream=True  # Enable streaming
        )

        logging.debug(f"Ollama API response status: {response.status_code}")

        generated_questions = []
        current_question = []  # Temporary list to hold tokens for the current question
        for line in response.iter_lines():
            if line:
                try:
                    json_line = json.loads(line)
                    if json_line.get('done'):
                        break  # Stop processing if done
                    current_question.append(json_line['response'])  # Collect tokens

                except json.JSONDecodeError:
                    logging.error("Received non-JSON response: %s", line)

        # Combine tokens into a single string for the final questions
        if current_question:
            full_questions = ''.join(current_question).strip()  # Join tokens into a single string and strip whitespace
            # Split the full_questions string into separate questions based on single newlines
            questions_list = full_questions.split('\n\n')  # Split by single newlines
            generated_questions.extend(questions_list)  # Add all questions to the generated_questions list

        logging.debug(f"Generated questions: {generated_questions}")

        # Limit the number of questions to the user-specified amount
        if len(generated_questions) > num_questions:
            generated_questions = generated_questions[:num_questions]

        # Clear existing questions and store new ones in the database
        clear_questions()
        store_questions(generated_questions)

        # Return as a JSON object
        return jsonify({"questions": generated_questions}), 200  # Return as JSON
    except Exception as e:
        logging.error(f"An error occurred: {str(e)}")  # Log the error message
        return jsonify({'error': 'An error occurred while processing the request.'}), 500

@app.route('/generate-papers', methods=['GET'])
def generate_papers():
    try:
        papers = []
        for i in range(10):  # Generate 10 different question papers
            questions = get_randomized_questions()

            # Limit the number of questions for each paper to whatever is available
            paper_questions = questions[:10]  # Get up to 10 questions for each paper
            papers.append(paper_questions)

            # Generate PDF for each paper
            pdf_filename = f'question_paper_{i + 1}.pdf'
            pdf_filepath = os.path.join(UPLOAD_FOLDER, pdf_filename)
            generate_pdf(paper_questions, pdf_filepath)

        return jsonify({"message": "Question papers generated successfully."}), 200
    except Exception as e:
        logging.error(f"An error occurred: {str(e)}")  # Log the error message
        return jsonify({'error': 'An error occurred while generating question papers.'}), 500

@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

def extract_text_from_pdf(filepath):
    text = ''
    with open(filepath, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + '\n'
            else:
                logging.warning("No text found on page.")
    return text

def generate_pdf(questions, filepath):
    doc = SimpleDocTemplate(filepath, pagesize=letter)
    styles = getSampleStyleSheet()
    
    elements = []
    for question in questions:
        elements.append(Paragraph(question, styles['BodyText']))
        elements.append(Spacer(1, 12))
    
    doc.build(elements)

if __name__ == '__main__':
    init_db()  # Initialize the database when the app starts
    app.run(debug=True)