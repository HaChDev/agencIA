"""
AgencIA - Test de Arquitectura Híbrida (SQL + Redis + LangGraph)
================================================================
Este script simula el ciclo de vida real:
1. Carga contexto de campaña desde SQL.
2. Invoca al DirectorAgent con el ID de la campaña.
3. El agente usa Redis para memoria transaccional y SQL para persistencia final.
"""

import json
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.infrastructure.postgres.database import SessionLocal
from app.db.repositories.campaign_repo import CampaignRepository
from app.agents.director.agent import DirectorAgent
from app.schemas.campaign import CampaignCreate


async def test(user_id: int, db_session: AsyncSession):
    """
    Función de prueba para el Director Agent integrada en las rutas de test.
    Usa la sesión inyectada por FastAPI.
    """
    results = []
    
    # 1. Setup de Datos (Usamos la sesión recibida)
    repo = CampaignRepository(db_session)
    
    # Intentamos obtener la última campaña del usuario
    campaigns = await repo.get_all_by_user(user_id=user_id, limit=1)
    
    if not campaigns:
        print(f"No se encontró campaña para user {user_id}, creando una de prueba...")
        campaign_data = CampaignCreate(
            user_id=user_id,
            camp_name=f"Campaña Test {uuid4().hex[:4]}",
            camp_brief_data={
                "objectives": ["Validar arquitectura híbrida", "Probar persistencia SQL"],
                "budget": 1000,
                "target_audience": "Desarrolladores de AgencIA"
            },
            camp_objective="Test de Integración"
        )
        campaign = await repo.create_campaign(campaign_data)
        # Hacemos commit explícito para que la campaña sea visible inmediatamente fuera de esta transacción
        await db_session.commit()
        # Refrescamos para mantener el objeto vinculado a la sesión (que ahora iniciará una nueva transacción)
        await db_session.refresh(campaign)
    else:
        campaign = campaigns[0]
        print(f"Usando campaña existente: {campaign.camp_name} (ID: {campaign.id})")

    campaign_id = campaign.id
    results.append({"event": "setup_complete", "campaign_id": campaign_id})

    # 2. Invocar al Agente Director
    agent = DirectorAgent()
    
    print(f"\nInvocando al Agente Director para campaña {campaign_id}...")
    
    try:
        async for event in agent.process_campaign(campaign_id=campaign_id, db_session=db_session):
            if "messages" in event:
                results.append({"node": list(event.keys())[0], "status": "processing"})
            else:
                results.append(event)
            
            print(f"   Evento: {list(event.keys())[0] if isinstance(event, dict) and event else 'Output'}")

    except Exception as e:
        print(f"Error en ejecución del agente: {e}")
        raise HTTPException(status_code=500, detail=f"Error en Agent Director: {str(e)}")

    return results
