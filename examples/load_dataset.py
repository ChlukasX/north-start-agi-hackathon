import pandas as pd
from datasets import load_dataset


def load_and_process_osm_data(dataset_name="ns2agi/antwerp-osm-navigator"):
    print(f"Loading dataset: {dataset_name}")
    dataset = load_dataset(dataset_name)

    print("\nDataset structure:")
    print(dataset)

    train_split = dataset["train"]
    print("\nShowing first 5 rows of the 'train' split:")
    print(train_split[:5])

    print("\nFiltering for 'node' types...")
    node_dataset = train_split.filter(lambda example: example["type"] == "node")
    print(f"Found {len(node_dataset)} nodes.")
    print("Showing first 5 nodes:")
    print(node_dataset[:5])

    print("\nConverting the all nodes to a pandas DataFrame...")
    df = node_dataset.to_pandas()

    print("\nPandas DataFrame head:")
    print(df.head())

    return df


if __name__ == "__main__":
    osm_dataframe = load_and_process_osm_data()
    output_path = "osm_nodes.csv"
    print(f"\nExporting DataFrame to {output_path}...")
    osm_dataframe.to_csv(output_path, index=False)
    print("Export complete.")

    print("\nScript finished.")

    print("\nScript finished.")
