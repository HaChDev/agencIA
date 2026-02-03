"""
AgencIA - Base Repository
=========================
Repositorio base con lógica de contención y reintentos (Robustez).
"""

import logging
import random
import asyncio
from typing import TypeVar, Generic, Optional, Any
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

# Configuración básica de logging
logger = logging.getLogger(__name__)

T = TypeVar("T")

class BaseRepository:
    """Clase base para todos los repositorios con lógica de seguridad."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def execute_with_retry(self, operation_func, max_retries: int = 3) -> Any:
        """
        Ejecuta una operación de base de datos con reintentos automáticos
        en caso de colisiones de integridad (e.g. PK duplicada).
        
        Args:
            operation_func: Función async que realiza la operación (add + commit).
            max_retries: Número máximo de intentos.
            
        Returns:
            El resultado de operation_func.
            
        Raises:
            IntegrityError: Si falla después de todos los reintentos.
        """
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                # Intentamos ejecutar la operación
                # Creamos un savepoint implícito con begin_nested para rollback parcial
                async with self.session.begin_nested():
                    result = await operation_func()
                    return result
                    
            except IntegrityError as e:
                last_exception = e
                # Verificamos si es error de unicidad (código 23505 en PostgreSQL)
                # O si es simplemente una colisión genérica
                logger.warning(
                    f"Intento {attempt + 1}/{max_retries} falló por IntegrityError: {str(e)}. Reintentando..."
                )
                
                if attempt < max_retries - 1:
                    # Backoff exponencial pequeñito con jitter para desincronizar hilos
                    sleep_time = (0.1 * (2 ** attempt)) + random.uniform(0.01, 0.05)
                    await asyncio.sleep(sleep_time)
                else:
                    logger.error("Todos los reintentos de DB fallaron.")
                    
            except Exception as e:
                # Otros errores no se reintentan
                raise e
        
        # Si salimos del loop, lanzamos la última excepción
        if last_exception:
            raise last_exception
