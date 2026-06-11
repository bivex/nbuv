import sys
from nbuv_oai import OAIClient as DSpaceClient
from openscience_oai import OpenScienceOAIClient

def search_repo(client, name, max_check=200):
    print(f"\nSearching {name} (checking up to {max_check} records)...")
    results = []
    
    # We use list_records. We can inspect the publication year in dc:date.
    try:
        records_generator = client.list_records()
        checked = 0
        for rec in records_generator:
            checked += 1
            if checked > max_check:
                break
                
            meta = rec['metadata']
            if not meta:
                continue
                
            # dc:date usually contains publication year(s)
            dates = meta.get('date', [])
            is_recent = False
            pub_year = None
            
            for d in dates:
                # Extract 4 digit year
                years = [part for part in d.replace('-', ' ').split() if len(part) == 4 and part.isdigit()]
                for y in years:
                    year_val = int(y)
                    if year_val >= 2025:
                        is_recent = True
                        pub_year = year_val
                        break
                if is_recent:
                    break
                    
            if is_recent:
                results.append((rec, pub_year))
                
    except Exception as e:
        print(f"Error querying {name}: {e}")
        
    return results

def main():
    dspace = DSpaceClient()
    openscience = OpenScienceOAIClient()
    
    # Let's search in both
    dspace_results = search_repo(dspace, "DSpace NBUV", max_check=300)
    openscience_results = search_repo(openscience, "Open Science LIBNAS", max_check=300)
    
    print("\n" + "="*80)
    print(" FOUND RECENT PUBLICATIONS (2025-2026) ")
    print("="*80)
    
    all_results = [("DSpace NBUV", r, y) for r, y in dspace_results] + \
                  ([("Open Science LIBNAS", r, y) for r, y in openscience_results])
                  
    if not all_results:
        print("No publications dated 2025 or 2026 found in the first batch of records.")
        return
        
    for source, rec, year in all_results:
        header = rec['header']
        meta = rec['metadata']
        
        title = ", ".join(meta.get('title', [])) if meta.get('title') else "No Title"
        creators = ", ".join(meta.get('creator', [])) if meta.get('creator') else "Unknown"
        subjects = ", ".join(meta.get('subject', [])) if meta.get('subject') else "None"
        description = " ".join(meta.get('description', [])) if meta.get('description') else ""
        urls = [u for u in meta.get('identifier', []) if u.startswith('http')]
        
        print(f"\n[{source}] Published: {year}")
        print(f"Title     : {title}")
        print(f"Creator(s): {creators}")
        if subjects != "None":
            print(f"Subject(s): {subjects}")
        if description:
            # truncate description
            desc_trunc = description[:200] + "..." if len(description) > 200 else description
            print(f"Abstract  : {desc_trunc}")
        if urls:
            print(f"URL       : {urls[0]}")
        print("-" * 50)

if __name__ == "__main__":
    main()
