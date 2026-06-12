import json
from database import ACTIVE_PERSONAS  # 1. Import your existing dictionary live

# 2. Open a new target JSON file for writing
with open("personas.json", "w", encoding="utf-8") as f:
    # 3. Cleanly serialize and dump the dictionary with formatting indents
    json.dump(ACTIVE_PERSONAS, f, indent=4, ensure_ascii=False)

print("Conversion complete! 'personas.json' has been created successfully.")