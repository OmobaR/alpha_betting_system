# run_simple.py
print("=" * 50)
print("ALPHABETTING SYSTEM - PHASE 1")
print("=" * 50)

import sys
sys.path.insert(0, "src")

try:
    # Try to import from pipeline module
    import pipeline
    print("✅ Pipeline module loaded")
    
    # If it has a main function, run it
    if hasattr(pipeline, 'main'):
        pipeline.main()
    elif hasattr(pipeline, 'Phase1FinalPipeline'):
        pipeline.Phase1FinalPipeline().run_demo()
    else:
        print("⚠️  No main function found. Running module directly.")
        # The module might run when imported
except Exception as e:
    print(f"❌ Error: {e}")
    print("\nTrying alternative import...")
    
    # Try running the file directly
    import subprocess
    result = subprocess.run([sys.executable, "src/pipeline.py"], 
                          capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)

print("\n" + "=" * 50)
print("PHASE 1 EXECUTION COMPLETE")
print("=" * 50)
