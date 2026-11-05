from ..data.repository import DataRepository


if __name__ == "__main__":
    snapshot_id = DataRepository().refresh()
    print(f"Snapshot créé : {snapshot_id}")
