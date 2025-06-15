import os
import shutil
import subprocess
import zipfile
import requests
from pathlib import Path
import sys

TEMP_DIR = Path("../temp")
OUTPUT_DIR = Path("../output")
TOOLS_DIR = Path("../tools")
FRIDA_GADGET_URL = "https://github.com/frida/frida/releases/download/16.0.19/frida-gadget-16.0.19-android-arm.so.xz"

APKTOOL_JAR_URL = "https://bitbucket.org/iBotPeaches/apktool/downloads/apktool_2.7.0.jar"

def ensure_apktool():
    apktool_jar = TOOLS_DIR / "apktool.jar"
    apktool_script = TOOLS_DIR / "apktool.bat" if sys.platform == "win32" else TOOLS_DIR / "apktool"
    
    if apktool_jar.exists() and apktool_script.exists():
        return apktool_script
    
    print("apktoolをセットアップしています...")
    TOOLS_DIR.mkdir(parents=True, exist_ok=True)
    
    response = requests.get(APKTOOL_JAR_URL, stream=True)
    response.raise_for_status()
    
    with open(apktool_jar, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    
    if sys.platform == "win32":
        with open(apktool_script, 'w') as f:
            f.write(f'@echo off\njava -jar "{apktool_jar}" %*')
    else:
        # Linux/Mac
        with open(apktool_script, 'w') as f:
            f.write(f'#!/bin/sh\njava -jar "{apktool_jar}" "$@"')
        os.chmod(apktool_script, 0o755)  # 実行権限を付与
    
    print(f"apktoolをセットアップしました: {apktool_script}")
    return apktool_script

def download_frida_gadget():
    # 既存のコードをそのまま使用
    print("Frida Gadgetをダウンロード中...")
    frida_path = TEMP_DIR / "frida-gadget.so.xz"
    
    response = requests.get(FRIDA_GADGET_URL, stream=True)
    response.raise_for_status()
    
    with open(frida_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    
    # XZファイルの解凍（Windowsでは外部コマンドが必要）
    try:
        # xzコマンドがあれば使用
        subprocess.run(["xz", "-d", str(frida_path)], check=True)
    except FileNotFoundError:
        print("xzコマンドが見つかりません。Pythonで解凍を試みます...")
        try:
            import lzma
            with lzma.open(frida_path, 'rb') as f_in:
                with open(TEMP_DIR / "frida-gadget.so", 'wb') as f_out:
                    f_out.write(f_in.read())
        except ImportError:
            print("lzmaモジュールがインストールされていません。")
            print("frida-gadget.soを手動で解凍してください。")
            sys.exit(1)
    
    return TEMP_DIR / "frida-gadget.so"

def inject_frida_gadget(apk_path):
    print(f"APKにFrida Gadgetをインジェクト中: {apk_path}")
    
    # apktoolを取得
    apktool = ensure_apktool()
    
    work_dir = TEMP_DIR / "apk_inject"
    # 既存ディレクトリの削除処理を強化
    if work_dir.exists():
        try:
            shutil.rmtree(work_dir)
        except PermissionError:
            print(f"警告: {work_dir}の削除に失敗しました。ディレクトリが使用中の可能性があります。")
    work_dir.mkdir(parents=True, exist_ok=True)
    
    print("APKの逆コンパイルを開始します（リソーススキップモード）...")
    try:
        subprocess.run([
            str(apktool), "d", str(apk_path), 
            "-o", str(work_dir), 
            "-f",  # 強制上書き
            "--no-res",  # リソースをデコードしない
            "--no-src",  # ソースコードをデコードしない(必要に応じて削除)
            "-r"   # リソースをデコードしない(古いバージョン互換)
        ], check=True)
    except subprocess.CalledProcessError:
        print("警告: 標準モードでの解析に失敗しました。代替モードを試行します...")
        try:
            subprocess.run([
                str(apktool), "d", str(apk_path), 
                "-o", str(work_dir), 
                "-f",
                "--no-res"
            ], check=True)
        except subprocess.CalledProcessError:
            print("警告: 代替モードでも失敗しました。最終モードを試行します...")
            subprocess.run([
                str(apktool), "d", str(apk_path), 
                "-o", str(work_dir), 
                "-f",
                "--no-res",
                "--only-main-classes"
            ], check=True)
    
    manifest_path = work_dir / "AndroidManifest.xml"
    smali_dir = work_dir / "smali"
    
    if not manifest_path.exists():
        print("警告: AndroidManifest.xmlが見つかりません。ZIPとして抽出を試みます...")
        with zipfile.ZipFile(apk_path, 'r') as zip_ref:
            try:
                zip_ref.extract('AndroidManifest.xml', work_dir)
            except KeyError:
                raise FileNotFoundError("AndroidManifest.xmlをAPKから抽出できませんでした")
    
    if not smali_dir.exists():
        smali_dir.mkdir(parents=True, exist_ok=True)
    
    frida_gadget = download_frida_gadget()
    
    if os.path.exists(os.path.join(os.path.dirname(apk_path), "config.arm64_v8a.apk")):
        print("ARM64アーキテクチャが検出されました")
        lib_dir = work_dir / "lib" / "arm64-v8a"
    else:
        lib_dir = work_dir / "lib" / "armeabi-v7a"
    
    lib_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(frida_gadget, lib_dir / "libfrida-gadget.so")
    
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = f.read()
    except UnicodeDecodeError:
        try:
            with open(manifest_path, "r", encoding="latin-1") as f:
                manifest = f.read()
        except Exception as e:
            print(f"マニフェストの読み取りエラー: {e}")
            print("バイナリ形式のマニフェストを処理中...")
            manifest = """<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <application android:name="io.frida.FridaApplication">
    </application>
</manifest>"""
            with open(manifest_path, "w", encoding="utf-8") as f:
                f.write(manifest)
    
    # アプリケーションタグを検索して修正（より堅牢に）
    if '<application ' in manifest and 'android:name="io.frida.FridaApplication"' not in manifest:
        manifest = manifest.replace(
            '<application ',
            '<application android:name="io.frida.FridaApplication" '
        )
        with open(manifest_path, "w", encoding="utf-8") as f:
            f.write(manifest)
    else:
        print("マニフェスト内の<application>タグの修正をスキップします")
    
    # FridaApplicationクラスを作成
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
    
    print("APKの再パッケージ化を開始します...")
    # APKを再構築（エラー処理を強化）
    modified_apk = OUTPUT_DIR / "injected.apk"
    try:
        subprocess.run([str(apktool), "b", str(work_dir), "-o", str(modified_apk), "--use-aapt2"], check=True)
    except subprocess.CalledProcessError:
        print("警告: AAPT2での再構築に失敗しました。標準AAPTで再試行します...")
        try:
            subprocess.run([str(apktool), "b", str(work_dir), "-o", str(modified_apk)], check=True)
        except subprocess.CalledProcessError:
            print("エラー: APKの再パッケージ化に失敗しました。手動での確認が必要です。")
            shutil.copy(apk_path, modified_apk)
            print(f"元のAPKを {modified_apk} にコピーしました。")
    
    keystore = OUTPUT_DIR / "debug.keystore"
    if not keystore.exists():
        try:
            print("デバッグ用キーストアを生成しています...")
            subprocess.run([
                "keytool", "-genkey", "-v", "-keystore", str(keystore),
                "-storepass", "android", "-alias", "androiddebugkey",
                "-keypass", "android", "-keyalg", "RSA", "-keysize", "2048",
                "-validity", "10000", "-dname", "CN=Android Debug,O=Android,C=US"
            ], check=True)
        except FileNotFoundError:
            print("keytoolが見つかりません。署名をスキップします。")
            return modified_apk
    
    try:
        signed_apk = OUTPUT_DIR / "injected-signed.apk"
        subprocess.run([
            "jarsigner", "-sigalg", "SHA1withRSA", "-digestalg", "SHA1",
            "-keystore", str(keystore), "-storepass", "android",
            "-keypass", "android", str(modified_apk), "androiddebugkey"
        ], check=True)
        
        shutil.move(modified_apk, signed_apk)
        
        print(f"インジェクト済みAPKが生成されました: {signed_apk}")
        return signed_apk
    except FileNotFoundError:
        print("jarsignerが見つかりません。署名されていないAPKを使用します。")
        print(f"未署名APKが生成されました: {modified_apk}")
        return modified_apk

def sign_apk(apk_path, output_name=None):
    """APKファイルに署名する共通関数"""
    if output_name is None:
        output_path = OUTPUT_DIR / f"signed-{os.path.basename(apk_path)}"
    else:
        output_path = OUTPUT_DIR / output_name
    
    print(f"APKに署名中: {apk_path} -> {output_path}")
    
    # 入力と出力が同じファイルの場合は一時ファイルを使用
    same_file = os.path.abspath(apk_path) == os.path.abspath(output_path)
    if same_file:
        temp_output = OUTPUT_DIR / f"temp_{os.path.basename(apk_path)}"
    else:
        temp_output = output_path
    
    # キーストアの確認と生成
    keystore = OUTPUT_DIR / "debug.keystore"
    if not keystore.exists():
        try:
            print("デバッグ用キーストアを生成しています...")
            subprocess.run([
                "keytool", "-genkey", "-v", "-keystore", str(keystore),
                "-storepass", "android", "-alias", "androiddebugkey",
                "-keypass", "android", "-keyalg", "RSA", "-keysize", "2048",
                "-validity", "10000", "-dname", "CN=Android Debug,O=Android,C=US"
            ], check=True)
        except FileNotFoundError:
            print("keytoolが見つかりません。署名をスキップします。")
            if not same_file:
                shutil.copy(apk_path, output_path)
            return output_path

    try:
        # より安全なアルゴリズムを使用（SHA-256/SHA-384/SHA-512）
        print("APKに署名を適用しています...")
        subprocess.run([
            "jarsigner", "-sigalg", "SHA256withRSA", "-digestalg", "SHA-256",
            "-keystore", str(keystore), "-storepass", "android",
            "-keypass", "android", str(apk_path), "androiddebugkey"
        ], check=True, encoding='utf-8')  # UTF-8エンコーディングを指定
        
        # 入力と出力が同じ場合は操作不要、それ以外はコピー
        if not same_file:
            shutil.copy(apk_path, output_path)
        
        print(f"署名が完了しました: {output_path}")
        return output_path
    except FileNotFoundError:
        print("jarsignerが見つかりません。署名されていないAPKを使用します。")
        if not same_file:
            shutil.copy(apk_path, output_path)
        return output_path

def main():
    xapk_extracted = TEMP_DIR / "xapk_extracted"
    
    manifest_path = xapk_extracted / "manifest.json"
    if manifest_path.exists():
        print("XAPKマニフェストを確認中...")
    
    # 複数のconfig APKに対応するためリスト形式に変更
    main_apk = None
    config_apks = []
    
    for root, dirs, files in os.walk(xapk_extracted):
        for file in files:
            if file.endswith('.apk'):
                apk_path = os.path.join(root, file)
                if 'config' in file.lower():
                    config_apks.append(apk_path)
                else:
                    main_apk = apk_path
    
    if not main_apk:
        raise FileNotFoundError("メインAPKファイルが見つかりませんでした")
    
    print(f"メインAPK: {main_apk}")
    if config_apks:
        print(f"設定APK: {', '.join(config_apks)}")
    
    injected_main_apk = inject_frida_gadget(main_apk)
    
    signed_config_apks = []
    if config_apks:
        print("\nスプリットAPKにも同じキーで署名します...")
        for config_apk in config_apks:
            config_name = os.path.basename(config_apk)
            # 一時コピーを作成してから署名
            temp_config = OUTPUT_DIR / config_name
            shutil.copy(config_apk, temp_config)
            signed_config_apk = sign_apk(temp_config, f"signed-{config_name}")
            signed_config_apks.append(signed_config_apk)
    
    if signed_config_apks:
        config_paths = " ".join([str(p) for p in signed_config_apks])
        print("\nインストール時は両方のAPKを指定してください:")
        print(f"adb install-multiple {injected_main_apk} {config_paths}")
    
    print("\n処理が完了しました！")
    
if __name__ == "__main__":
    main()