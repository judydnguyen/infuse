import os, json

results = []

for name in os.listdir("."):
    if not os.path.isdir(name):
        continue
    if os.path.islink(name):
        continue

    total = 0
    for root, dirs, files in os.walk(name, followlinks=False):
        for f in files:
            p = os.path.join(root, f)
            if not os.path.islink(p):
                total += os.path.getsize(p)

    results.append({"path": name, "size_bytes": total})

results.sort(key=lambda x: x["size_bytes"], reverse=True)

with open("disk_usage.json", "w") as f:
    json.dump(results[:5], f, indent=2)