with open("frontend/index.html", "r", encoding="utf-8") as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    if "Bishop Heber Quick Links" in line:
        print(f"Quick Links widget starts at line {idx+1}")
        # print 20 lines
        for j in range(max(0, idx - 2), min(len(lines), idx + 25)):
            print(f"  {j+1}: {lines[j].rstrip()}")
        break
