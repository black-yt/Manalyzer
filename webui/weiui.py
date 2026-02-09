from flask import Flask, render_template, request, jsonify
import os
import time
from flask_cors import CORS
import json

app = Flask(__name__)
CORS(app)


while not os.path.exists('data/save_info.json'):
    print("Waiting for save_info.json to be created...")
    time.sleep(1)

with open('data/save_info.json', 'r', encoding='utf-8') as file:
    save_dir = json.load(file)[0]

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/submit_info', methods=['POST'])
def submit_info():
    field = request.form.get('field', '')
    topic_of_interest = request.form.get('topic_of_interest', '')
    table_template = request.form.get('table_template', '')
    
    with open('data/user_input.json', 'w', encoding='utf-8') as f:
        json.dump({'filed': field, 'topic_of_interest': topic_of_interest, 'table_template': table_template}, f, ensure_ascii=False, indent=4)
    
    return jsonify({'status': 'success'})

@app.route('/get_chat_log')
def get_chat_log():
    try:
        with open('data/chat.log', 'r') as f:
            content = f.read()
        return jsonify({'content': content})
    except FileNotFoundError:
        return jsonify({'content': 'No log file found'})

@app.route('/get_file_structure')
def get_file_structure():
    def build_tree(path):
        tree = {'name': os.path.basename(path), 'children': []}
        try:
            if os.path.isdir(path):
                sons = os.listdir(path)
                sons_dir = sorted([son for son in sons if os.path.isdir(os.path.join(path, son))])
                sons_file = sorted([son for son in sons if os.path.isfile(os.path.join(path, son))])
                sons = sons_dir + sons_file
                for item in sons:
                    full_path = os.path.join(path, item)
                    tree['children'].append(build_tree(full_path))
            return tree
        except PermissionError:
            return {'name': f"{os.path.basename(path)} (permission denied)", 'children': []}
    
    output_tree = build_tree(save_dir)
    return jsonify({'children': output_tree['children']})

@app.route('/get_progress')
def get_progress():
    try:
        with open('data/chat.log', 'r') as f:
            content = f.read()

        if 'Reporter' in content:
            progress_level = 5
        elif 'DataAnalyst' in content:
            progress_level = 4
        elif 'DataExtratorWithChecker' in content:
            progress_level = 3
        elif 'PaperReviewer' in content:
            progress_level = 2
        else:
            progress_level = 1
        
        return jsonify({'progress': progress_level})
    except FileNotFoundError:
        return jsonify({'progress': 0})

if __name__ == '__main__':
    app.run(debug=True, port=5000)