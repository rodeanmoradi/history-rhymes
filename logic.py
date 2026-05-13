from datasets import load_dataset

dataset = load_dataset("wikimedia/structured-wikipedia", "20240916.en", split="train", streaming=True)