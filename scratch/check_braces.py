with open("frontend/index.html", "r", encoding="utf-8") as f:
    html = f.read()

# Find <script> starting from line 2321 to the end
start_marker = "<script>"
script_start = html.find(start_marker, 20000) # search starting around position 20000
if script_start == -1:
    script_start = html.find(start_marker)

script_end = html.find("</script>", script_start)
script_content = html[script_start + len(start_marker):script_end]

# Verify braces matching
open_braces = 0
close_braces = 0
line_num = 1
brace_stack = []

for idx, char in enumerate(script_content):
    if char == '\n':
        line_num += 1
    elif char == '{':
        open_braces += 1
        brace_stack.append(line_num)
    elif char == '}':
        close_braces += 1
        if brace_stack:
            brace_stack.pop()
        else:
            print(f"Extra close brace at line {line_num}!")

print(f"Total open braces: {open_braces}")
print(f"Total close braces: {close_braces}")
if brace_stack:
    print(f"Unclosed braces opened at lines: {brace_stack}")
else:
    print("All braces are properly closed!")
