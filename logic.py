from datasets import load_dataset

dataset = load_dataset("wikimedia/structured-wikipedia", "20240916.en", split="train", streaming=True)

# Create historical filter by doing keyword search on abstract and name
it = iter(dataset)
print(next(it)["abstract"])
print(next(it)["abstract"])