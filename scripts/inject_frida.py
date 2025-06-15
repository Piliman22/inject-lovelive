import os
import shutil
import subprocess
import zipfile
import requests
from pathlib import Path

TEMP_DIR = Path("../temp")
OUTPUT_DIR = Path("../output")
FRIDA_GADGET_URL = "https://github.com/frida/frida/releases/download/16.0.19/frida-gadget-16.0.19-android-arm.so.xz"

def download_frida_gadget():
    print("Frida Gadgetをダウンロード中...")
    frida_path = TEMP_DIR / "frida-gadget.so.xz"
    
    response = requests.get(FRIDA_GADGET_URL, stream=True)
    response.raise_for_status()
    
    with open(frida_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    
    subprocess.run(["xz", "-d", str(frida_path)], check=True)
    
    return TEMP_DIR / "frida-gadget.so"

def inject_frida_gadget(apk_path):
    print(f"APKにFrida Gadgetをインジェクト中: {apk_path}")
    
    work_dir = TEMP_DIR / "apk_inject"
    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True)
    
    subprocess.run(["apktool", "d", str(apk_path), "-o", str(work_dir)], check=True)
    
    frida_gadget = download_frida_gadget()
    
    # lib/armeabi-v7a/にfrida-gadget.soをコピー
    lib_dir = work_dir / "lib" / "armeabi-v7a"
    lib_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(frida_gadget, lib_dir / "libfrida-gadget.so")
    
    # AndroidManifest.xmlを修正してFrida Gadgetをロードするように変更
    # ここでは簡易的な実装を示しています。実際にはより複雑な処理が必要かもしれません
    manifest_path = work_dir / "AndroidManifest.xml"
    with open(manifest_path, "r") as f:
        manifest = f.read()
    
    # アプリケーションタグにprocessを追加
    manifest = manifest.replace(
        '<application ',
        '<application android:name="io.frida.FridaApplication" '
    )
    
    with open(manifest_path, "w") as f:
        f.write(manifest)
    
    # io.frida.FridaApplicationクラスを作成
    java_dir = work_dir / "smali" / "io" / "frida"
    java_dir.mkdir(parents=True, exist_ok=True)
    
    frida_app_path = java_dir / "FridaApplication.smali"
    with open(frida_app_path, "w") as f:
        f.write("""
.class public Lio/frida/FridaApplication;
.super Landroid/app/Application;
.source "FridaApplication.java"

# direct methods
.method public constructor <init>()V
    .locals 0
    
    .line 1
    invoke-direct {p0}, Landroid/app/Application;-><init>()V
    
    return-void
.end method

# virtual methods
.method public attachBaseContext(Landroid/content/Context;)V
    .locals 2
    .param p1, "base"    # Landroid/content/Context;
    
    .line 5
    invoke-super {p0, p1}, Landroid/app/Application;->attachBaseContext(Landroid/content/Context;)V
    
    .line 6
    const-string v0, "frida-gadget"
    
    invoke-static {v0}, Ljava/lang/System;->loadLibrary(Ljava/lang/String;)V
    
    .line 7
    return-void
.end method
""")
    
    # APKを再構築
    modified_apk = OUTPUT_DIR / "injected.apk"
    subprocess.run(["apktool", "b", str(work_dir), "-o", str(modified_apk)], check=True)
    
    # APK署名
    keystore = OUTPUT_DIR / "debug.keystore"
    if not keystore.exists():
        subprocess.run([
            "keytool", "-genkey", "-v", "-keystore", str(keystore),
            "-storepass", "android", "-alias", "androiddebugkey",
            "-keypass", "android", "-keyalg", "RSA", "-keysize", "2048",
            "-validity", "10000", "-dname", "CN=Android Debug,O=Android,C=US"
        ], check=True)
    
    signed_apk = OUTPUT_DIR / "injected-signed.apk"
    subprocess.run([
        "jarsigner", "-sigalg", "SHA1withRSA", "-digestalg", "SHA1",
        "-keystore", str(keystore), "-storepass", "android",
        "-keypass", "android", str(modified_apk), "androiddebugkey"
    ], check=True)
    
    shutil.move(modified_apk, signed_apk)
    
    print(f"インジェクト済みAPKが生成されました: {signed_apk}")
    return signed_apk

def main():
    # APKを取得（download_and_extract.pyで抽出されたAPKを使用）
    xapk_extracted = TEMP_DIR / "xapk_extracted"
    apk_path = None
    
    for root, dirs, files in os.walk(xapk_extracted):
        for file in files:
            if file.endswith('.apk'):
                apk_path = os.path.join(root, file)
                break
        if apk_path:
            break
    
    if not apk_path:
        raise FileNotFoundError("APKファイルが見つかりませんでした")
    
    inject_frida_gadget(apk_path)

if __name__ == "__main__":
    main()