"""
AgencIA - Test Script (Director PhD + RAG + Redis)
==================================================
Prueba de integración completa.
"""

import asyncio
import os
from dotenv import load_dotenv


from app.agents.director.agent import DirectorAgent

TEST_BRIEF = {
    "client_name": "EcoModa S.A.",
    "industry": "Moda Sostenible",
    "budget": "$500,000 COP",
    "goal": "Lanzar nueva línea de ropa hecha de plástico reciclado en Colombia.",
    "target_audience": "Millennials conscientes del medio ambiente."
}

async def main():
    print("Iniciando prueba del Director de Estrategia...")
    
    try:
        agent = DirectorAgent()
        
        print(f"Procesando brief para: {TEST_BRIEF['client_name']}")
        
        async for event in agent.process_brief(
            client_id="ecomoda_test",
            brief=TEST_BRIEF
        ):
            # Imprimir eventos de progreso
            for node, data in event.items():
                print(f"Nodo completado: {node}")
                if "current_phase" in data:
                    print(f"Fase: {data['current_phase']}")
                if "current_critique" in data:
                    print(f"Crítica recibida: {data['current_critique'][:100]}...")
                if "tasks" in data:
                    print(f"Tareas generadas: {len(data['tasks'])}")
                    
        print("Proceso finalizado exitosamente.")

        return "Proceso finalizado exitosamente."
        
    except Exception as e:
        print(f"Error crítico: {str(e)}")
        import traceback
        traceback.print_exc()
        return f"Error crítico: {str(e)}"
