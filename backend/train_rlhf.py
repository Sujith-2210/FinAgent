
import asyncio
from app.services.rlhf_service import RLHFService

async def run_training_pipeline():
    print("🚀 Starting RLHF Data Pipeline...")
    
    service = RLHFService()
    
    print("1. Processing Feedback Logs...")
    try:
        result = await service.export_dataset()
        print(f"✅ Dataset Exported: {result['path']}")
        print(f"📊 Stats: {result['stats']}")
        
        print("\n2. Ready for Training Framework (e.g., HuggingFace TRL)")
        print("   Command: python train_dpo.py --dataset data/rlhf_dataset.json")
        print("   (This step requires GPU and is out of scope for this prototype)")
        
    except Exception as e:
        print(f"❌ Pipeline Failed: {e}")

if __name__ == "__main__":
    asyncio.run(run_training_pipeline())
