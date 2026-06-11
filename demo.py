#!/usr/bin/env python3
import sys
from nbuv_oai import OAIClient as DSpaceClient
from openscience_oai import OpenScienceOAIClient

def print_section(title: str):
    print("\n" + "="*70)
    print(f" {title} ")
    print("="*70)

def demo_dspace():
    print_section("DEMO 1: NBUV DSpace Repository (dspace.nbuv.gov.ua)")
    client = DSpaceClient()

    # Identify
    info = client.identify()
    print(f"Repository Name : {info.get('repositoryName')}")
    print(f"Base URL        : {info.get('baseURL')}")
    print(f"Admin Email     : {info.get('adminEmail')}")

    # List first 3 Sets
    print("\n--- Collections (First 3) ---")
    for idx, s in enumerate(client.list_sets()):
        if idx >= 3:
            print("... and more sets available.")
            break
        print(f"Spec: {s['setSpec']:<20} | Name: {s['setName']}")

    # List first 2 Records
    print("\n--- Records (First 2) ---")
    for idx, rec in enumerate(client.list_records()):
        if idx >= 2:
            break
        meta = rec['metadata']
        print(f"ID   : {rec['header'].get('identifier')}")
        if meta:
            print(f"Title: {', '.join(meta.get('title', []))}")
            print(f"Dates: {', '.join(meta.get('date', []))}")
        print()

def demo_openscience():
    print_section("DEMO 2: LIBNAS Open Science Portal (open-science.nbuv.gov.ua)")
    client = OpenScienceOAIClient()

    # Identify
    info = client.identify()
    print(f"Repository Name : {info.get('repositoryName')}")
    print(f"Base URL        : {info.get('baseURL')}")
    print(f"Admin Email     : {info.get('adminEmail')}")

    # List Sets (Gracefully handled!)
    print("\n--- Collections ---")
    sets = list(client.list_sets())
    print(f"Total Sets Found: {len(sets)}")

    # List first 2 Records
    print("\n--- Records (First 2) ---")
    for idx, rec in enumerate(client.list_records()):
        if idx >= 2:
            break
        meta = rec['metadata']
        print(f"ID   : {rec['header'].get('identifier')}")
        if meta:
            print(f"Title: {', '.join(meta.get('title', []))}")
            print(f"Dates: {', '.join(meta.get('date', []))}")
        print()

def main():
    try:
        demo_dspace()
        demo_openscience()
    except Exception as e:
        print(f"\nAn error occurred during execution: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
