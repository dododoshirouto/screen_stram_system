if exist dist\screen_stream.exe (
    remove dist\screen_stream.exe
)

venv\Scripts\python.exe -m PyInstaller --onefile --noconsole ^
    --name "screen_stream" ^
    --icon "icons/on.ico" ^
    --add-data "client_secret_458758854605-ihia8ttepcfjeab3k80lk1rc40dttso9.apps.googleusercontent.com.json;." ^
    --add-data "icons/off.png;icons" ^
    --add-data "icons/on.png;icons" ^
    --add-data "icons/mosaic.png;icons" ^
    --add-data "icons/black.png;icons" ^
    screen_stream.py
@REM pause
