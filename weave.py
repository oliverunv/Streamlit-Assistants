import weaviate
from weaviate.classes.init import Auth
from weaviate.classes.config import Property, DataType
from dotenv import load_dotenv
import os
import pandas as pd

# Step 1: Connect to Weaviate
load_dotenv()
cluster_url = os.getenv("WEAVIATE_URL")
api_key = os.getenv("WEAVIATE_API_KEY")

client = weaviate.connect_to_weaviate_cloud(
    cluster_url=cluster_url,
    auth_credentials=Auth.api_key(api_key),
)

# Step 2: Ensure schema has the correct metadata properties
properties_to_add = [
    ("part", DataType.TEXT),
    ("section", DataType.TEXT),
    ("title", DataType.TEXT),
    ("un_charter_article", DataType.TEXT),
    ("rules_of_procedure_article", DataType.TEXT),
    ("icj_article", DataType.TEXT),
    ("intro_note", DataType.TEXT),
]

collection = client.collections.get("U5a280054_textembedding3small_1536")

for name, dtype in properties_to_add:
    try:
        collection.config.add_property(Property(name=name, data_type=dtype))
        print(f"✅ Added property: {name}")
    except Exception as e:
        print(f"⚠️ Could not add {name}: {e}")

# Step 3: Load metadata from CSV
df = pd.read_csv("Metadata.csv")

metadata_lookup = {
    row["filename"]: {
        "part": row["Part"],
        "section": row["Section"],
        "title": row["Title"],
        "un_charter_article": row["UN Charter Article"],
        "rules_of_procedure_article": row["Rules of Procedure Article"],
        "icj_article": row["Statute of the International Court of Justice Article "],
        "intro_note": row["Intro note"]
    }
    for _, row in df.iterrows()
}

# Step 4: Iterate and update
updated_count = 0
total_objects = 0
unmatched_filenames = []

for obj in collection.iterator():
    total_objects += 1
    filename = obj.properties.get("metadata", {}).get("filename", "")

    if filename in metadata_lookup:
        metadata = metadata_lookup[filename]
        clean_metadata = {k: ("" if pd.isna(v) else v) for k, v in metadata.items()}
        collection.data.update(uuid=obj.uuid, properties=clean_metadata)
        updated_count += 1
        print(f"✅ Updated: {filename}")
    else:
        unmatched_filenames.append(filename)

# Step 5: Report summary
print(f"\n🧮 Total objects scanned: {total_objects}")
print(f"✅ Total updated with metadata: {updated_count}")
print(f"❌ Objects NOT updated (filename not in CSV): {len(unmatched_filenames)}")

if unmatched_filenames:
    print("\n🧾 Sample unmatched filenames from Weaviate:")
    for fn in unmatched_filenames[:10]:
        print("-", fn)

client.close()
