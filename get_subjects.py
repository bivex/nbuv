from collections import Counter
from nbuv_oai import OAIClient
from openscience_oai import OpenScienceOAIClient

def collect_subjects(client, name, max_records=200):
    print(f"Collecting subjects from {name} (first {max_records} records)...")
    subjects_counter = Counter()
    try:
        records = client.list_records()
        for idx, rec in enumerate(records):
            if idx >= max_records:
                break
            meta = rec['metadata']
            if meta and 'subject' in meta:
                for subject in meta['subject']:
                    # Clean and normalize
                    subj_clean = subject.strip()
                    if subj_clean:
                        subjects_counter[subj_clean] += 1
    except Exception as e:
        print(f"Error: {e}")
    return subjects_counter

def main():
    dspace = OAIClient()
    openscience = OpenScienceOAIClient()
    
    ds_subjects = collect_subjects(dspace, "DSpace NBUV", 300)
    os_subjects = collect_subjects(openscience, "Open Science LIBNAS", 300)
    
    print("\n" + "="*50)
    print(" MOST FREQUENT SUBJECT CATEGORIES (dc:subject) ")
    print("="*50)
    
    print("\n--- DSpace NBUV ---")
    for subj, count in ds_subjects.most_common(15):
        print(f"[{count:<2} records] {subj}")
        
    print("\n--- Open Science LIBNAS ---")
    for subj, count in os_subjects.most_common(15):
        print(f"[{count:<2} records] {subj}")

if __name__ == "__main__":
    main()
