import os
import tarfile
import zipfile
import subprocess
from pathlib import Path

def decompile_nested(input_dir: str, output_dir: str, cfr_jar: str = "./cfr.jar", process_nested: bool = False):
    input_path = Path(input_dir).resolve()
    output_path = Path(output_dir).resolve()
    cfr_path = Path(cfr_jar).resolve()
    tmp_path = Path(f"./tmp_decompile_{os.urandom(4).hex()}").resolve()

          
    if not input_path.exists():
        print(f"错误：输入目录 {input_path} 不存在！")
        return
    if not cfr_path.exists():
        print(f"错误：CFR 工具 {cfr_path} 不存在！")
        return
    output_path.mkdir(parents=True, exist_ok=True)
    tmp_path.mkdir(parents=True, exist_ok=True)

             
    def _decompile_single(file: Path, rel_root: Path):
        rel_file = file.relative_to(rel_root)
        out_subdir = output_path / rel_file.parent
        out_subdir.mkdir(parents=True, exist_ok=True)
        print(f"处理：{rel_file}")

        if file.suffix in (".jar", ".war"):
                         
            cmd = [
                "java", "-jar", str(cfr_path), str(file),
                "--outputdir", str(out_subdir),
                "--decodelambdas", "true",
                "--hideutf", "false",
                "--silent", "true"
            ]
            subprocess.run(cmd, capture_output=True, text=True)

                      
            if process_nested:
                jar_tmp = tmp_path / file.stem
                jar_tmp.mkdir(exist_ok=True)
                try:
                    with zipfile.ZipFile(file, "r") as zf:
                        zf.extractall(jar_tmp)
                except:
                    pass
                            
                for nested_jar in jar_tmp.rglob("*.jar"):
                    nested_rel = nested_jar.relative_to(jar_tmp)
                    nested_out = out_subdir / nested_rel.parent
                    nested_out.mkdir(parents=True, exist_ok=True)
                    cmd_nested = [
                        "java", "-jar", str(cfr_path), str(nested_jar),
                        "--outputdir", str(nested_out),
                        "--decodelambdas", "true",
                        "--hideutf", "false",
                        "--silent", "true"
                    ]
                    subprocess.run(cmd_nested, capture_output=True, text=True)

        elif file.suffix == ".class":
                           
            out_file = output_path / rel_file.with_suffix(".java")
            cmd = [
                "java", "-jar", str(cfr_path), str(file),
                "--outputfile", str(out_file),
                "--decodelambdas", "true",
                "--hideutf", "false",
                "--silent", "true"
            ]
            subprocess.run(cmd, capture_output=True, text=True)

              
    print(f"开始递归扫描 {input_path} ...")
    for file in input_path.rglob("*"):
        if file.is_file() and file.suffix in (".jar", ".war", ".class"):
            _decompile_single(file, input_path)

            
    import shutil
    shutil.rmtree(tmp_path, ignore_errors=True)
    print(f"完成！反编译文件在：{output_path}")

      
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("用法：python decompiler.py <输入目录> <输出目录> [处理嵌套JAR: true/false]")
    else:
        process_nested = sys.argv[3].lower() == "true" if len(sys.argv) > 3 else False
        decompile_nested(sys.argv[1], sys.argv[2], process_nested=process_nested)
