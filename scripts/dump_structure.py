FILE = r"C:\Program Files (x86)\World of Warcraft\_retail_\WTF\Account\124283120#1\SavedVariables\Auctionator.lua"

with open(FILE, "r", encoding="utf-8", errors="ignore") as f:
    data = f.read()

start = data.find("AUCTIONATOR_PRICE_DATABASE")

if start == -1:
    print("NOT FOUND")
    exit()

block = data[start:start+5000]  # on prend un gros chunk

print(block)