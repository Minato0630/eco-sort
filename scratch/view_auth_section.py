with open("frontend/index.html", "r", encoding="utf-8") as f:
    lines = f.readlines()

auth_view_start = -1
for idx, line in enumerate(lines):
    if 'id="authView"' in line:
        auth_view_start = idx
        break

if auth_view_start != -1:
    print(f"authView found at line {auth_view_start+1}")
    for j in range(auth_view_start, min(len(lines), auth_view_start + 120)):
        print(f"{j+1}: {lines[j].rstrip()}")
else:
    print("authView not found!")
