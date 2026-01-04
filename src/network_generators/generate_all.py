"""
Generate All Networks
=====================
Convenience script to run all network generators in sequence.
"""

from datetime import datetime


def main():
    """Run all network generators."""
    start_time = datetime.now()
    print("=" * 60)
    print("SAN - Generate All Networks")
    print("=" * 60)
    
    generators = [
        ("Pass Networks", "src.network_generators.pass_networks"),
        ("Match Networks", "src.network_generators.match_networks"),
        ("Player-Team Networks", "src.network_generators.player_team_networks"),
        ("Field Networks", "src.network_generators.field_networks"),
        ("Unified Pass Network", "src.network_generators.unified_pass_network"),
    ]
    
    results = []
    
    for name, module_path in generators:
        print(f"\n{'─' * 60}")
        print(f"▶ {name}")
        print("─" * 60)
        
        try:
            # Dynamic import and run
            module = __import__(module_path, fromlist=['main'])
            module.main()
            results.append((name, "✓ Success"))
        except Exception as e:
            results.append((name, f"✗ Failed: {e}"))
            print(f"Error: {e}")
    
    # Summary
    duration = datetime.now() - start_time
    print(f"\n{'=' * 60}")
    print("SUMMARY")
    print("=" * 60)
    for name, status in results:
        print(f"  {name}: {status}")
    print(f"\nTotal time: {duration}")
    print("=" * 60)


if __name__ == "__main__":
    main()
