# LoveLive APKダンプ＆Fridaインジェクションツール

このリポジトリは、LoveLive（com.oddno.lovelive）のAPKファイルからIl2Cppダンプを取得し、Frida Gadgetをインジェクトするためのツールセットです。

## 機能

- APKPureから最新のLoveLive XAPKを自動ダウンロード
- XAPKからil2cpp.soとglobal-metadata.datを抽出
- Il2CppDumperを使用してdump.csを生成
- GitHub Releasesにdump.csを自動アップロード
- APKにFrida Gadgetをインジェクトして、動的解析を可能にする

## 必要なツール

- Python 3.8以上
- apktool
- jarsigner
- keytool
- xz（xz-utilsパッケージ）

## セットアップ

```bash
# リポジトリをクローン
git clone https://github.com/yourusername/inject-linklike.git
cd inject-linklike

# 必要なPythonパッケージをインストール
pip install requests
```

## 使い方

### 1. XAPKのダウンロードと必要ファイルの抽出

```bash
python scripts/download_and_extract.py
```

このスクリプトは、APKPureから最新のLoveLive XAPKをダウンロードし、Il2Cpp関連ファイルを抽出します。

### 2. IL2Cpp Dumpの生成

```bash
python scripts/generate_dump.py
```

Il2CppDumperを使用してdump.csを生成します。

### 3. Frida Gadgetのインジェクト

```bash
python scripts/inject_frida.py
```

APKにFrida Gadgetをインジェクトし、デバッグ可能なAPKを生成します。

### 4. 自動リリース

GitHub Actionsを有効にすることで、毎週自動的に最新のdump.csを生成してリリースすることができます。

## ライセンス

MITライセンス