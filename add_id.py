import json

# Step 1: Read the JSON data from the file
with open('data.json', 'r') as file:
    data = json.load(file)

# Step 2: Modify the data by adding an 'id' field
for index, item in enumerate(data, start=0):
    item["id"] = index

# Step 3: Write the modified data back to a new file (or overwrite the original file)
with open('modified_data.json', 'w') as file:
    json.dump(data, file, indent=4)