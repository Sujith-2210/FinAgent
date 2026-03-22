
import asyncio
import os
import shutil
from unittest.mock import AsyncMock

from app.services.graph_db import GraphDBService
from app.services.sandbox import SandboxService
from app.agents.graph_reasoning import GraphReasoningAgent
from app.agents.code import CodeAgent

WORKSPACE_DIR = "demo_workspace"

async def run_demo():
    print("🚀 Starting FinAgent Final Integration Demo...")
    print("Scenario: Supply Chain Risk Analysis for 'FutureCar'\n")

    # --- 1. Setup Infrastructure ---
    print("1️⃣  Initializing Infrastructure...")
    try:
        # Graph DB
        graph_db = GraphDBService()
        await graph_db.verify_connectivity()
        
        # Sandbox
        if os.path.exists(WORKSPACE_DIR):
            shutil.rmtree(WORKSPACE_DIR)
        sandbox = SandboxService(workspace=WORKSPACE_DIR)
        
        # Agents
        graph_agent = GraphReasoningAgent(graph_db)
        code_agent = CodeAgent(sandbox)
        
        # Mock LLM for Code Agent to ensure deterministic demo visualization
        code_agent.invoke_llm = AsyncMock()
        
        print("✅ Services and Agents ready.\n")
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        return

    # --- 2. Populate Knowledge Graph ---
    print("2️⃣  Populating Knowledge Graph (Supply Chain)...")
    try:
        await graph_db.ensure_constraints()
        
        # Create Entities
        await graph_db.create_node("Company", {"name": "FutureCar", "ticker": "FCAR"})
        await graph_db.create_node("Company", {"name": "BatteryCo", "ticker": "BATT"})
        await graph_db.create_node("Company", {"name": "LithiumMine", "ticker": "LITH"})
        
        # Create Relationships (Chain)
        # FutureCar <--BUYER-- BatteryCo <--BUYER-- LithiumMine
        await graph_db.create_relationship(
            {"label": "Company", "name": "LithiumMine"},
            {"label": "Company", "name": "BatteryCo"},
            "SUPPLIES"
        )
        await graph_db.create_relationship(
            {"label": "Company", "name": "BatteryCo"},
            {"label": "Company", "name": "FutureCar"},
            "SUPPLIES"
        )
        
        print("✅ Graph populated: LithiumMine -> BatteryCo -> FutureCar\n")
    except Exception as e:
        print(f"❌ Population failed: {e}")
        return

    # --- 3. Graph Reasoning (Multi-Hop) ---
    print("3️⃣  Agent 1: Graph Reasoning Agent")
    print("   Query: 'What is the impact of LithiumMine?'")
    
    try:
        graph_impact_query = {
            "query_topic": "impact of LithiumMine",
            "analysis_type": "network"
        }
        graph_result = await graph_agent.process(graph_impact_query)
        
        trace = graph_result.get("raw_data", [])
        print(f"   🔍 Reasoning Trace:")
        for step in trace:
            print(f"      - {step}")
            
        print(f"   💡 Conclusion: {graph_result.get('conclusion')}\n")
        
    except Exception as e:
        print(f"❌ Graph analysis failed: {e}")

    # --- 4. Code Execution (Quantitative Analysis) ---
    print("4️⃣  Agent 2: Code Agent")
    print("   Query: 'Plot the projected revenue impact on FutureCar'")
    
    # Mocking the LLM generation to produce specific plotting code
    mock_plot_code = """
import matplotlib.pyplot as plt
import numpy as np

# Simulate data
years = np.array([2024, 2025, 2026, 2027, 2028])
revenue_bau = np.array([100, 120, 150, 180, 220])
revenue_impact = np.array([100, 115, 130, 140, 150]) # Impact of shortage

plt.figure(figsize=(10, 6))
plt.plot(years, revenue_bau, 'g--', label='BAU Revenue ($B)')
plt.plot(years, revenue_impact, 'r-', label='With Supply Disruption ($B)')
plt.fill_between(years, revenue_bau, revenue_impact, color='red', alpha=0.1)
plt.title("FutureCar Revenue Risk Analysis")
plt.xlabel("Year")
plt.ylabel("Revenue ($ Billions)")
plt.legend()
plt.grid(True)
print("Plot generated successfully.")
"""
    code_agent.invoke_llm.return_value = {
        "code": mock_plot_code,
        "explanation": "Plotting revenue projection comparing BAU vs Disruption scenario."
    }
    
    try:
        code_query = {"query_topic": "Plot revenue impact"}
        code_result = await code_agent.process(code_query)
        
        print(f"   💻 Generated Code:\n{code_result.get('code')[:50]}...")
        print(f"   ⚙️  Execution Output: {code_result.get('output').strip()}")
        
        images = code_result.get("images", [])
        if images:
            print(f"   🖼️  Chart Generated: {images[0]['name']} (Size: {len(images[0]['base64'])} bytes)")
        else:
            print("   ⚠️  No chart generated.")
            
        print("\n✅ Demo Complete!")
        
    except Exception as e:
        print(f"❌ Code execution failed: {e}")

    # --- Cleanup ---
    print("\n🧹 Cleaning up...")
    await graph_db.execute_query("MATCH (n) WHERE n.name IN ['FutureCar', 'BatteryCo', 'LithiumMine'] DETACH DELETE n")
    await graph_db.close()
    if os.path.exists(WORKSPACE_DIR):
        print(f"   (Workspace {WORKSPACE_DIR} preserved for inspection)")
        # shutil.rmtree(WORKSPACE_DIR) 

if __name__ == "__main__":
    asyncio.run(run_demo())
