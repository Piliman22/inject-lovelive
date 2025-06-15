import os
import requests
import zipfile
import shutil
from pathlib import Path

XAPK_URL = "https://d.apkpure.com/b/XAPK/com.oddno.lovelive?version=latest"
IL2CPP_DUMPER_URL = "https://github.com/Perfare/Il2CppDumper/releases/download/v6.7.46/Il2CppDumper-win-v6.7.46.zip"
TEMP_DIR = Path("../temp")
TOOLS_DIR = Path("../tools")
OUTPUT_DIR = Path("../output")

def setup_directories():
    for dir_path in [TEMP_DIR, TOOLS_DIR, OUTPUT_DIR]:
        dir_path.mkdir(exist_ok=True, parents=True)

def download_file(url, save_path):
    print(f"ダウンロード中: {url}")
    response = requests.get(url, stream=True)
    response.raise_for_status()
    
    with open(save_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    
    return save_path

def extract_zip(zip_path, extract_to):
    print(f"解凍中: {zip_path} → {extract_to}")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)

def extract_il2cpp_files(xapk_dir):
    """XAPKからil2cpp.soとglobal-metadata.datを抽出"""
    print("il2cpp.soとglobal-metadata.datを探索中...")
    
    apk_dir = None
    for root, dirs, files in os.walk(xapk_dir):
        for file in files:
            if file.endswith('.apk'):
                apk_path = os.path.join(root, file)
                apk_extract_dir = TEMP_DIR / "apk_extracted"
                apk_extract_dir.mkdir(exist_ok=True)
                extract_zip(apk_path, apk_extract_dir)
                apk_dir = apk_extract_dir
                break
        if apk_dir:
            break
    
    if not apk_dir:
        raise FileNotFoundError("APKファイルが見つかりませんでした")
    
    il2cpp_so = None
    global_metadata = None
    
    for root, dirs, files in os.walk(apk_dir):
        for file in files:
            if file == "libil2cpp.so":
                il2cpp_so = os.path.join(root, file)
            elif file == "global-metadata.dat":
                global_metadata = os.path.join(root, file)
        
        if il2cpp_so and global_metadata:
            break
    
    if not il2cpp_so or not global_metadata:
        raise FileNotFoundError("libil2cpp.so または global-metadata.dat が見つかりませんでした")
    
    shutil.copy(il2cpp_so, OUTPUT_DIR)
    shutil.copy(global_metadata, OUTPUT_DIR)
    
    print(f"抽出完了: {OUTPUT_DIR / 'libil2cpp.so'}, {OUTPUT_DIR / 'global-metadata.dat'}")
    return OUTPUT_DIR / "libil2cpp.so", OUTPUT_DIR / "global-metadata.dat"

def main():
    setup_directories()
    
    xapk_path = TEMP_DIR / "lovelive.xapk"
    download_file(XAPK_URL, xapk_path)
    xapk_extract_dir = TEMP_DIR / "xapk_extracted"
    extract_zip(xapk_path, xapk_extract_dir)
    
    il2cpp_dumper_path = TEMP_DIR / "Il2CppDumper.zip"
    download_file(IL2CPP_DUMPER_URL, il2cpp_dumper_path)
    extract_zip(il2cpp_dumper_path, TOOLS_DIR / "Il2CppDumper")
    
    il2cpp_so, global_metadata = extract_il2cpp_files(xapk_extract_dir)
    
    print("ダウンロードと抽出が完了しました。")
    print(f"Il2Cppファイル：{il2cpp_so}, {global_metadata}")
    print(f"Il2CppDumper：{TOOLS_DIR / 'Il2CppDumper'}")

if __name__ == "__main__":
    main()