import PyInstaller.__main__
import os
import sys
import shutil
import winshell  # Thư viện để tạo shortcut trên Windows
from win32com.client import Dispatch

def create_shortcut(exe_path, working_dir):
    """Tạo shortcut trên Desktop với working directory cụ thể"""
    desktop = winshell.desktop()  # Lấy đường dẫn đến Desktop
    shortcut_path = os.path.join(desktop, 'Taara_Notepad++.lnk')  # Tên shortcut
    shell = Dispatch('WScript.Shell')
    shortcut = shell.CreateShortCut(shortcut_path)
    shortcut.Targetpath = exe_path  # Đường dẫn đến file exe
    shortcut.WorkingDirectory = working_dir  # Thư mục làm việc
    shortcut.IconLocation = exe_path  # Dùng icon của chính file exe
    shortcut.save()
    print(f"Đã tạo shortcut tại: {shortcut_path}")

def clean_up():
    """Xóa các file và thư mục không cần thiết sau khi build"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    items_to_remove = [
        os.path.join(current_dir, 'Taara_Notepad++.exe.spec'),  # File .spec
        os.path.join(current_dir, 'Taara_Notepad++.spec'),      # File .spec
        os.path.join(current_dir, 'build'),      # Thư mục build
        os.path.join(current_dir, 'backups'),    # Thư mục backups
        os.path.join(current_dir, 'dist'),       # Thư mục dist
        os.path.join(current_dir, 'test'),       # Thư mục test
    ]
    
    for item in items_to_remove:
        if os.path.exists(item):
            if os.path.isfile(item):
                os.remove(item)
                print(f"Đã xóa file: {item}")
            elif os.path.isdir(item):
                shutil.rmtree(item)
                print(f"Đã xóa thư mục: {item}")

def build_exe():
    # Đường dẫn tới thư mục hiện tại
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Các file Python cần build
    files = [
        os.path.join(current_dir, 'main.py'),
        os.path.join(current_dir, 'ctags_handler.py'),
        os.path.join(current_dir, 'project_view.py'),
    ]
    
    # Kiểm tra các file Python có tồn tại không
    for file_path in files:
        if not os.path.exists(file_path):
            print(f"Error: File {file_path} không tồn tại!")
            sys.exit(1)

    # Đường dẫn tới thư mục chứa các file SVG (thư mục 'icons')
    svg_folder = os.path.join(current_dir, 'icons')
    themes_folder = os.path.join(current_dir, 'themes')

    # Kiểm tra thư mục icons
    if not os.path.exists(svg_folder):
        print(f"Error: Thư mục {svg_folder} không tồn tại!")
        sys.exit(1)

    # Lấy tất cả file .svg trong thư mục
    svg_files = [f for f in os.listdir(svg_folder) if f.endswith('.svg')]
    if not svg_files:
        print(f"Warning: Không tìm thấy file .svg nào trong thư mục {svg_folder}")

    # Lấy tất cả file .json trong thư mục themes
    json_theme_files = [f for f in os.listdir(themes_folder) if f.endswith('.json')]
    if not json_theme_files:
        print(f"Warning: Không tìm thấy file .json nào trong thư mục {themes_folder}")

    # Đường dẫn tới file session.json
    json_file = os.path.join(current_dir, 'session.json')

    # Cấu hình lệnh PyInstaller
    pyinstaller_args = [
        '--onefile',            # Build thành một file exe duy nhất
        '--clean',              # Xóa các file tạm trước khi build
        '--noconsole',          # Không hiển thị console khi chạy
        '--noupx',              # Không sử dụng UPX để nén
        '-F',                   # Tương tự --onefile
        '-n', 'Taara_Notepad++.exe',        # Tên file exe đầu ra
        '--icon', 'icons/logoIcon.ico',    # Đường dẫn đầy đủ tới icon
        '--distpath', '.',      # Đầu ra tại thư mục hiện tại
    ]
    
    # Thêm tất cả file .svg như dữ liệu đi kèm
    for svg_file in svg_files:
        svg_path = os.path.join(svg_folder, svg_file)
        pyinstaller_args.append(f'--add-data={svg_path}:icons')  # Sửa cú pháp

    # Thêm tất cả file .json trong thư mục themes như dữ liệu đi kèm
    for json_theme_file in json_theme_files:
        json_theme_path = os.path.join(themes_folder, json_theme_file)
        pyinstaller_args.append(f'--add-data={json_theme_path}:themes')

    # Thêm file session.json như dữ liệu đi kèm
    pyinstaller_args.append(f'--add-data={json_file}:.')  # Đặt trong thư mục gốc khi giải nén

    # Thêm tất cả các file Python vào lệnh
    pyinstaller_args.extend(files)
    
    try:
        print("Đang build file exe...")
        print(f"Tìm thấy {len(svg_files)} file SVG: {svg_files}")
        PyInstaller.__main__.run(pyinstaller_args)
        print(f"Build hoàn tất! File exe được tạo trong thư mục '{current_dir}'")
        
        # Dọn dẹp sau khi build
        print("Đang dọn dẹp các file và thư mục không cần thiết...")
        clean_up()

        # Tạo shortcut trên Desktop
        print("Đang tạo shortcut trên Desktop...")
        create_shortcut(f"{current_dir}/Taara_Notepad++.exe", current_dir)
        
    except Exception as e:
        print(f"Build thất bại: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    build_exe()