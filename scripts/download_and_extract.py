import os
import requests
import zipfile
import shutil
from pathlib import Path

XAPK_URL = "https://apkcombo.com/r2?u=https%3A%2F%2Fapks.39b7cb94d40914bac590886981b0ed6e.r2.cloudflarestorage.com%2Fcom.oddno.lovelive%2F4.1.10%2F86517.6afe26ed6421caba1e81b00a3acc76374155d19e.apks%3Fresponse-content-disposition%3Dattachment%253B%2520filename%253D%2522Link%25EF%25BC%2581Like%25EF%25BC%2581%25E3%2583%25A9%25E3%2583%2596%25E3%2583%25A9%25E3%2582%25A4%25E3%2583%2596%25EF%25BC%2581%25E8%2593%25AE%25E3%2583%258E%25E7%25A9%25BA%25E3%2582%25B9%25E3%2582%25AF%25E3%2583%25BC%25E3%2583%25AB%25E3%2582%25A2%25E3%2582%25A4%25E3%2583%2589%25E3%2583%25AB%25E3%2582%25AF%25E3%2583%25A9%25E3%2583%2596_4.1.10_apkcombo.com.xapk%2522%26response-content-type%3Dapplication%252Fxapk-package-archive%26X-Amz-Algorithm%3DAWS4-HMAC-SHA256%26X-Amz-Date%3D20250615T034727Z%26X-Amz-SignedHeaders%3Dhost%26X-Amz-Expires%3D14400%26X-Amz-Credential%3D3cb727b4cd4780c410b780ac7caa4da3%252F20250615%252Fauto%252Fs3%252Faws4_request%26X-Amz-Signature%3D51e3e922f91fe430920010eace04e6a99ff667c30da4a1c7883ded1a1404521f&fp=df425fcee0565cf6d4561887ea1a35ed&package_name=com.oddno.lovelive&lang=ja"
IL2CPP_DUMPER_URL = "https://github.com/Perfare/Il2CppDumper/releases/download/v6.7.46/Il2CppDumper-win-v6.7.46.zip"
TEMP_DIR = Path("../temp")
TOOLS_DIR = Path("../tools")
OUTPUT_DIR = Path("../output")

session = requests.Session()

def setup_directories():
    for dir_path in [TEMP_DIR, TOOLS_DIR, OUTPUT_DIR]:
        dir_path.mkdir(exist_ok=True, parents=True)

def download_file(url, save_path):
    """ファイルをダウンロードして保存"""
    print(f"ダウンロード中: {url}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Referer': 'https://apkpure.com/',
    }
    
    response = session.get(url, stream=True, headers=headers,allow_redirects=True)
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
    
    # すべてのAPKファイルを抽出するディレクトリ
    apk_extract_dir = TEMP_DIR / "apk_extracted"
    if apk_extract_dir.exists():
        shutil.rmtree(apk_extract_dir)
    apk_extract_dir.mkdir(exist_ok=True)
    
    apk_files_found = 0
    for root, dirs, files in os.walk(xapk_dir):
        for file in files:
            if file.endswith('.apk'):
                apk_path = os.path.join(root, file)
                print(f"APKファイルを解凍中: {apk_path}")
                
                apk_specific_dir = apk_extract_dir / f"apk_{apk_files_found}"
                apk_specific_dir.mkdir(exist_ok=True)
                
                try:
                    extract_zip(apk_path, apk_specific_dir)
                    apk_files_found += 1
                except zipfile.BadZipFile:
                    print(f"警告: {apk_path} は有効なZIPファイルではありません。スキップします。")
    
    if apk_files_found == 0:
        raise FileNotFoundError("XAPKディレクトリ内にAPKファイルが見つかりませんでした")
    
    print(f"{apk_files_found}個のAPKファイルを解凍しました")
    
    il2cpp_so = None
    global_metadata = None
    
    for root, dirs, files in os.walk(apk_extract_dir):
        for file in files:
            if file == "libil2cpp.so" or file.endswith("il2cpp.so"):
                il2cpp_so = os.path.join(root, file)
                print(f"libil2cpp.so を発見: {il2cpp_so}")
            elif file == "global-metadata.dat":
                global_metadata = os.path.join(root, file)
                print(f"global-metadata.dat を発見: {global_metadata}")
        
        if il2cpp_so and global_metadata:
            break
    
    if not il2cpp_so or not global_metadata:
        print("標準の場所で見つからないため、より広範囲で検索しています...")
        for root, dirs, files in os.walk(apk_extract_dir):
            for file in files:
                if not il2cpp_so and ("il2cpp" in file.lower() and file.endswith(".so")):
                    il2cpp_so = os.path.join(root, file)
                    print(f"代替のlibil2cpp.so を発見: {il2cpp_so}")
                elif not global_metadata and "global-metadata" in file.lower():
                    global_metadata = os.path.join(root, file)
                    print(f"代替のglobal-metadata.dat を発見: {global_metadata}")
            
            if il2cpp_so and global_metadata:
                break
    
    if not il2cpp_so or not global_metadata:
        print("\nデバッグ情報: 抽出されたファイル一覧")
        for root, dirs, files in os.walk(apk_extract_dir):
            for file in files:
                if ".so" in file or "metadata" in file:
                    print(f" - {os.path.join(root, file)}")
        
        raise FileNotFoundError("libil2cpp.so または global-metadata.dat が見つかりませんでした")
    
    shutil.copy(il2cpp_so, OUTPUT_DIR)
    shutil.copy(global_metadata, OUTPUT_DIR)
    
    il2cpp_dest = OUTPUT_DIR / "libil2cpp.so"
    metadata_dest = OUTPUT_DIR / "global-metadata.dat"
    
    if os.path.basename(il2cpp_so) != "libil2cpp.so":
        os.rename(OUTPUT_DIR / os.path.basename(il2cpp_so), il2cpp_dest)
    
    if os.path.basename(global_metadata) != "global-metadata.dat":
        os.rename(OUTPUT_DIR / os.path.basename(global_metadata), metadata_dest)
    
    print(f"抽出完了: {il2cpp_dest}, {metadata_dest}")
    return il2cpp_dest, metadata_dest

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