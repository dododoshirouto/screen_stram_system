IF NOT EXIST venv (
    python -m venv venv
)

If NOT EXIST requirements.txt (
    venv\Scripts\python.exe -m pip freeze > requirements.txt
)

venv\Scripts\python.exe -m pip install -r requirements.txt
