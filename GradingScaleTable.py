import webbrowser
from flask import Flask
import threading
import time

app = Flask(__name__)

def open_browser():
    time.sleep(2)  # Wait for server to start
    webbrowser.open('http://127.0.0.1:5000')

@app.route('/')
def home():
    return "Hello World"

if __name__ == '__main__':
    threading.Timer(1, open_browser).start()
    app.run(debug=True)


    
#Graing Scale Table
grading_table = [{"letter_grade": "A+", "grade_point": 4.0,"point_range": "3.85 - 4.00", "performance": "Execellent"}, 
                 {"letter_grade": "A", "grade_point": 4.0,"point_range": "3.70 - 3.84", "performance": "Execellent"}]
app.run()