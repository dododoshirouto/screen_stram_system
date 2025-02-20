pyinstaller --onefile ^
    --add-data "icons/off.png;icons" ^
    --add-data "icons/on.png;icons" ^
    --add-data "icons/mosaic.png;icons" ^
    --add-data "icons/black.png;icons" ^
    screen_stream.py
pause