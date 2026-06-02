FILE = r"C:\Program Files (x86)\World of Warcraft\_retail_\WTF\Account\124283120#1\SavedVariables\Auctionator.lua"

with open(FILE, "r", encoding="utf-8", errors="ignore") as f:
    data = f.read()

keys = []

for line in data.splitlines():
    if "AUCTIONATOR" in line:
        keys.append(line.strip())

print("\n".join(keys[:200]))