with open("frontend/index.html", "r", encoding="utf-8") as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    if "</script>" in line and idx > 3600:
        print(f"Script tag ends at line {idx+1}: {line.strip()}")
        # print 5 lines before
        for j in range(idx - 6, idx + 2):
            print(f"  {j+1}: {lines[j].rstrip()}")
        break
