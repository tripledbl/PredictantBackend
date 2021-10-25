# Set up (after cd into project directory):
## create and activate virtual environment (prerequisite: must have python installed)
    * python3 -m venv venv
    * venv\Scripts\activate
## install dependencies in virtual environment (cmd/powershell)
    * pip install -r requirements.txt
## initialize env vars
    * $env:FLASK_APP = "app"
    * $env:FLASK_ENV = "development"
## run on local server (http://127.0.0.1:5000/)
    * flask run
