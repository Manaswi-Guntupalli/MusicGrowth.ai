from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.services.similarity import get_similarity_model, load_reference_dataset


def main() -> None:
    refs = load_reference_dataset()
    model = get_similarity_model()
    print("Trained similarity model successfully")
    print(f"Reference tracks loaded: {len(refs)}")
    print(f"Feature count: 9")
    print(f"Model type: {type(model['nn']).__name__}")
    print(f"Cluster model: {type(model['kmeans']).__name__}")
    print(f"Cluster count: {model['kmeans'].n_clusters}")
    labels = model["cluster_labels"]
    print("Cluster labels:")
    for cluster_id in sorted(labels.keys()):
        print(f"  {cluster_id}: {labels[cluster_id]}")


if __name__ == "__main__":
    main()
