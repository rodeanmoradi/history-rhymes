from datasets import load_dataset

dataset = load_dataset("wikimedia/structured-wikipedia", "20240916.en", split="train", streaming=True)

# Create historical filter by doing keyword search on abstract and name; TODO: Add more keywords and handle edge cases
def word_search(dataset):
    if dataset["abstract"] != None:
        if "words" in dataset["abstract"]:
            return True    
    if "words" in dataset["name"]:
        return True
    
    return False

historical_dataset = dataset.filter(word_search)