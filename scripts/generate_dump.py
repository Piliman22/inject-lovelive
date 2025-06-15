import os
import subprocess
import shutil
from pathlib import Path

OUTPUT_DIR = Path("../output")
TOOLS_DIR = Path("../tools")
IL2CPP_DUMPER_DIR = TOOLS_DIR / "Il2CppDumper"

def run_il2cpp_dumper():
    print("Il2CppDumperを実行中...")
    
    il2cpp_so = OUTPUT_DIR / "libil2cpp.so"
    global_metadata = OUTPUT_DIR / "global-metadata.dat"
    
    if not il2cpp_so.exists() or not global_metadata.exists():
        raise FileNotFoundError(f"必要なファイルが見つかりません: {il2cpp_so} or {global_metadata}")
    
    dumper_exe = IL2CPP_DUMPER_DIR / "Il2CppDumper.exe"
    
    if not dumper_exe.exists():
        raise FileNotFoundError(f"Il2CppDumper.exeが見つかりません: {dumper_exe}")
    
    result = subprocess.run(
        [
            str(dumper_exe),
            str(il2cpp_so),
            str(global_metadata),
            str(OUTPUT_DIR / "dump")
        ],
        input="1\n",
        text=True,
        check=True,
        capture_output=True
    )
    
    print(result.stdout)
    
    dump_cs_path = OUTPUT_DIR / "dump" / "script" / "dump.cs"
    if dump_cs_path.exists():
        shutil.copy(dump_cs_path, OUTPUT_DIR)
        print(f"dump.csが生成されました: {OUTPUT_DIR / 'dump.cs'}")
    else:
        raise FileNotFoundError(f"dump.csが生成されませんでした: {dump_cs_path}")

def main():
    run_il2cpp_dumper()
    print("dump.csの生成が完了しました")

if __name__ == "__main__":
    main()