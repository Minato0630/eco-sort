with open("frontend/index.html", "r", encoding="utf-8") as f:
    html = f.read()

import re

# find style block
style_block = re.findall(r'<style>(.*?)</style>', html, re.DOTALL)
if style_block:
    css = style_block[0]
    print("=== EXTRACTED STYLE SNIPPETS ===")
    lines = css.splitlines()
    for i, l in enumerate(lines):
        if any(w in l.lower() for w in ["overflow", "height", "scroll", "body", "html", "modal-overlay"]):
            # print surrounding lines
            start = max(0, i - 2)
            end = min(len(lines), i + 3)
            print(f"CSS Line {i+1}:")
            for idx in range(start, end):
                print(f"  {lines[idx]}")
            print("-" * 30)
else:
    print("Style block not found!")
