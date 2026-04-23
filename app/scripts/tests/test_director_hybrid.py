"""
AgencIA - Test de Arquitectura Híbrida (SQL + Redis + LangGraph)
=================================================================
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
from app.db.models.campaign import CampaignStatus


async def test(user_id: int):
    """
    Función de prueba para el Director Agent integrada en las rutas de test.
    El agente crea su propia sesión independiente, así que no necesitamos
    pasar la sesión de FastAPI.
    """
    results = []

    # 1. Setup de Datos - crear campaña si no existe
    # Usar una sesión PROPIA para el setup para evitar problemas con la sesión de FastAPI
    async with SessionLocal() as setup_session:

        repo = CampaignRepository(setup_session)
        campaign =  await repo.get_all_by_user(user_id, status=CampaignStatus.ACTIVE, limit=1)
        campaign = campaign[0] if campaign else None

        if not campaign:
            print(
                f"No se encontró campaña activa para user {user_id}, creando una de prueba..."
            )
            campaign_data = CampaignCreate(
                user_id=user_id,
                camp_name=f"Campaña Test {uuid4().hex[:4]}",
                camp_brief_data={
                    "objectives": [
                        "Validar arquitectura híbrida",
                        "Probar persistencia SQL",
                    ],
                    "budget": 1000,
                    "target_audience": "Desarrolladores de AgencIA",
                },
                camp_objective="Test de Integración",
            )
            campaign = await repo.create_campaign(campaign_data)
            await setup_session.commit()
            await setup_session.refresh(campaign)
        else:
            print(f"Usando campaña existente: {campaign.camp_name} (ID: {campaign.id})")

        campaign_id = campaign.id
        results.append({"event": "setup_complete", "campaign_id": campaign_id})

    # 2. Invocar al Agente Director SIN pasar db_session
    # El agente crea su propia sesión independiente
    agent = DirectorAgent()

    print(f"\nInvocando al Agente Director para campaña {campaign_id}...")

    try:
        # No pasar db_session - el agente maneja su propia conexión
        async for event in agent.process_campaign(
            campaign_id=campaign_id, db_session=None
        ):
            if "messages" in event:
                results.append({"node": list(event.keys())[0], "status": "processing"})
            else:
                results.append(event)

            print(
                f"   Evento: {list(event.keys())[0] if isinstance(event, dict) and event else 'Output'}"
            )

    except Exception as e:
        print(f"Error en ejecución del agente: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error en Agent Director: {str(e)}"
        )

    return results
