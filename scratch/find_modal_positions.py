with open("frontend/index.html", "r", encoding="utf-8") as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    if "<!-- FORGOT PASSWORD MODAL -->" in line:
        print(f"forgotPasswordModal starts at line {idx+1}")
    if "<!-- MOCK COMMUNICATIONS POPUP" in line:
        print(f"communicationSimulation starts at line {idx+1}")
    if "</main>" in line and idx > 2200:
        print(f"main close tag at line {idx+1}")
    if "<!-- Script Logic -->" in line:
        print(f"script logic start at line {idx+1}")
