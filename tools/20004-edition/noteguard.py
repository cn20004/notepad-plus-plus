#!/usr/bin/env python3
"""20004 NoteGuard: non-destructive backup of existing Notepad++ recovery data.
Does not change source files or claim to save in-memory unsaved buffers.
"""
import argparse
import datetime as datetime
import hashlib
import json
import os
import shutil
from pathlib import Path

def digest(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""):
            h.update(block)
    return h.hexdigest()

def archive(source, destination):
    source=Path(source).expanduser().resolve()
    destination=Path(destination).expanduser().resolve()
    if not source.is_dir(): raise ValueError("Source directory not found")
    if destination==source or source in destination.parents:
        raise ValueError("Destination must be outside the original Notepad++ data directory")
    if destination in source.parents:
        raise ValueError("Destination cannot be a parent of source")
    stamp=datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    target=destination/("NotepadPP-Recovery-"+stamp)
    target.mkdir(parents=True,exist_ok=False)
    files=[]
    try:
        for path in source.rglob("*"):
            if not path.is_file(): continue
            rel=path.relative_to(source)
            # Do not follow symlinks into unrelated data.
            if path.is_symlink(): continue
            dst=target/rel
            dst.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(path,dst)
            original_hash=digest(path)
            copy_hash=digest(dst)
            if original_hash!=copy_hash: raise IOError(f"Backup verification failed: {rel}")
            files.append({"path":str(rel),"bytes":dst.stat().st_size,"sha256":copy_hash})
        manifest={"source":str(source),"created":datetime.datetime.now().isoformat(),"files":files,
                  "note":"Copy only; unsaved memory buffers not captured. Verify recovery separately."}
        (target/"manifest-20004.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
    except Exception:
        shutil.rmtree(target,ignore_errors=True)
        raise
    return target,len(files)

def main():
    p=argparse.ArgumentParser(description="Backup Notepad++ session and recovery files without modifying originals")
    p.add_argument("--source",default=str(Path(os.environ.get("APPDATA",str(Path.home())))/"Notepad++"))
    p.add_argument("--dest",required=True,help="Independent backup directory, ideally another physical disk")
    a=p.parse_args()
    path,count=archive(a.source,a.dest)
    print(f"Verified {count} files: {path}")
if __name__=="__main__": main()
