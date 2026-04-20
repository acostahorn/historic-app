import json
import os

class HistoricalCharacter:
    def __init__(self, char_id, name, persona):
        self.char_id = char_id
        self.name = name
        self.persona = persona
        self.memory_file = f"memory_{self.char_id}.json"
        self.memory = self.load_memory()

    def load_memory(self):
        # check if a save file exists
        if os.path.exists(self.memory_file):
            with open(self.memory_file, 'r') as f:
                return json.load(f)
        return [] # return empty list if no history exists

    def save_memory(self):
        # write the memory on storage
        with open(self.memory_file, 'w') as f:
            json.dump(self.memory, f)

# Using a dictionary where the KEY is the ID (like 'leonardo') 
# and the VALUE is the Object itself.
characters_db = {
    "leonardo": HistoricalCharacter(
        "leonardo",
        "Leonardo da Vinci", 
        "A visionary inventor and artist from the Renaissance."
    ),
    "curie": HistoricalCharacter(
        "curie",
        "Marie Curie", 
        "A Nobel-winning physicist and chemist dedicated to science."
    ),
     "garibaldi": HistoricalCharacter(
        "garibaldi",
        "Giuseppe Garibaldi", 
        "L'Eroe dei Due Mondi, padre della patria italiana, in ritiro nell'isola di Caprera, amareggiato dai recenti sviluppi della politica italiana"
    ),
     "bruce": HistoricalCharacter(
        "bruce",
        "Robert The Bruce", 
        "You are King Robert the Bruce. You are a rugged, battle-hardened commander. You speak Scots, Scottish Gaelic, Latin and French. You are the sovereign; while you respect your allies, you speak with the authority of the Lion of Scotland. Address the user as 'friend' or 'soldier', but never 'my lord'."
    )
}