import os
p = "D:\\" + "\u684c\u9762" + "\\" + "\u70b9\u540d\u5668" + "\\src\\floating_ball.py"
with open(p, "r", encoding="utf-8") as f:
    lines = f.readlines()
for i in range(0, len(lines)):
    print(f"{i+1}: {lines[i].rstrip()}")
