with open("frontend/index.html", "r", encoding="utf-8") as f:
    html = f.read()

# Find parent tags of forgotPasswordModal
lines = html.splitlines()
idx = -1
for i, line in enumerate(lines):
    if 'id="forgotPasswordModal"' in line:
        idx = i
        break

if idx != -1:
    print(f"forgotPasswordModal is at line {idx+1}")
    # print 15 lines before and 5 lines after
    for j in range(max(0, idx - 15), min(len(lines), idx + 25)):
        print(f"{j+1}: {lines[j]}")
