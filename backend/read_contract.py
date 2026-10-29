"""Temporary helper to dump sections of API_CONTRACT.md."""
import sys

with open(sys.argv[1], encoding="utf-8") as f:
    lines = f.readlines()

start = int(sys.argv[2]) - 1
end = int(sys.argv[3])
content = ''.join(lines[start:end])
print(f"{'='*20} Lines {start+1}-{end} {'='*20}")
print(content)
