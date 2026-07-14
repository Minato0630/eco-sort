with open("C:/Users/pandi/PROJECTS/waste-sorting-ml/frontend/index.html", "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if "<script" in line:
        print(f"Script tag starts at line {i+1}: {line.strip()}")
    if "function toggleAuthMode" in line:
        print(f"toggleAuthMode at line {i+1}: {line.strip()}")
    if "function submitAuth" in line:
        print(f"submitAuth at line {i+1}: {line.strip()}")
    if "function updateProfile" in line:
        print(f"updateProfile at line {i+1}: {line.strip()}")
    if "function enterApp" in line:
        print(f"enterApp at line {i+1}: {line.strip()}")
