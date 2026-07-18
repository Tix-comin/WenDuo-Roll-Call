import os
import shutil
root = r"d:\桌面\点名器"
src = os.path.join(root, "dist", "WenDuoPicker.exe")
dst = os.path.join(root, "dist", "闻铎点名器.exe")

if os.path.exists(src):
    if os.path.exists(dst):
        try:
            os.remove(dst)
        except Exception:
            pass
    try:
        os.rename(src, dst)
        print("OK: renamed")
    except Exception as e:
        print(f"Rename failed: {e}")
        if not os.path.exists(dst):
            shutil.copy2(src, dst)
            print(f"OK: copied to {dst}")
else:
    print("Source not found:", src)
