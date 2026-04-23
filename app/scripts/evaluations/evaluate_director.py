"""
AgencIA - Pipeline de Evaluación (LLM-as-a-judge)
=================================================
Este script provee utilidades para evaluar la calidad de las estrategias producidas
por el `DirectorAgent` contra rúbricas de evaluación estrictas.

Uso:
    Se puede integrar con LangSmith Datasets o usar programáticamente en tests unitarios.
"""

import json
from typing import Dict, Any, List
from pydantic import BaseModel, Field

# Intentamos cargar LangChain Chat моделей
try:
    from langchain_openai import ChatOpenAI
    from langchain_groq import ChatGroq
except ImportError:
    pass

from app.core.config import settings

class EvaluationResult(BaseModel):
    """Esquema esperado de salida del juez LLM"""
    coherence_score: int = Field(..., description="Puntuación de 1 a 10 evaluando si la estrategia tiene sentido y buena narrativa.")
    brief_coverage_score: int = Field(..., description="Puntuación de 1 a 10 evaluando qué tantos puntos del brief original se cubrieron.")
    budget_adherence: bool = Field(..., description="Verdadero si la estrategia respetó los limitantes de presupuesto.")
    critical_analysis: str = Field(..., description="Razonamiento crítico del juez (feedback).")
    final_passed: bool = Field(..., description="Aprobado general de calidad mínima viable.")

def get_judge_llm():
    """Genera una instancia de LLM altamente confiable para evaluación."""
    # Usualmente gpt-4o es el estándar de oro para LLM-as-a-judge
    # Aquí usamos la configuración base, intentando usar OpenAI si está o Groq como respaldo.
    if settings.OPENAI_API_KEY:
        try:
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(model="gpt-4o", temperature=0.0)
        except Exception:
            pass
            
    if settings.GROQ_API_KEY:
        from langchain_groq import ChatGroq
        # Llama-3-70b es excelente para razonamiento estricto
        return ChatGroq(model="llama3-70b-8192", temperature=0.0)
        
    raise ValueError("Se requiere OPENAI_API_KEY o GROQ_API_KEY para correr las evaluaciones.")

async def evaluate_strategy(briefing: Dict[str, Any], strategy: str) -> EvaluationResult:
    """
    Evalúa una estrategia (salida) en contra de su briefing original (entrada)
    y retorna un resultado estructurado calificándola.
    """
    llm = get_judge_llm()
    
    # Instrucciones estrictas para el juez
    system_prompt = (
        "Eres un Juez Evaluador Experto de Estrategias de Marketing y Operaciones.\n"
        "Tu misión es evaluar fríamente la estrategia suministrada basándote en el Brief Original del cliente.\n"
        "Analiza paso a paso y sé muy exigente.\n\n"
        "Reglas:\n"
        "1. Revisa si respetaron presupuestos y audiencias mencionadas.\n"
        "2. Evalúa si el texto tiene sentido profesional.\n"
        "3. Debes proveer una salida compatible con el esquema de evaluación provisto."
    )
    
    user_prompt = f"""
    === BRIEF ORIGINAL DEL CLIENTE ===
    {json.dumps(briefing, indent=2, ensure_ascii=False)}
    
    === ESTRATEGIA GENERADA (SALIDA A EVALUAR) ===
    {strategy}
    """
    
    # Langchain structured_output hace que el LLM fuerza la salida como JSON respetando pydantic.
    structured_llm = llm.with_structured_output(EvaluationResult)
    
    from langchain_core.messages import SystemMessage, HumanMessage
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]
    
    print("\n[Evaluation] Evocando al Juez LLM...")
    result: EvaluationResult = await structured_llm.ainvoke(messages)
    
    return result

async def run_sample_evaluation():
    """Prueba rápida de la lógica de evaluación"""
    sample_brief = {
        "objectives": ["Aumentar ventas 20%", "Lanzamiento en LatAm"],
        "budget": 5000,
        "target_audience": "Jóvenes universitarios de 18-24"
    }
    
    sample_strategy = (
        "Para lograr el aumento de ventas, destinaremos los $5000 USD por completo "
        "en campañas de TikTok y Twitch, apuntadas a LatAm, ya que allí está nuestra "
        "audiencia demográfica objetivo de estudiantes (18 a 24 años)."
    )
    
    print("Corriendo Evaluación Analítica...")
    res = await evaluate_strategy(sample_brief, sample_strategy)
    
    print(f"\n===== RESULTADO DE EVALUACIÓN =====")
    print(f"Coherencia: {res.coherence_score}/10")
    print(f"Cobertura Brief: {res.brief_coverage_score}/10")
    print(f"¿Respetó presupuesto?: {'Sí' if res.budget_adherence else 'No'}")
    print(f"Análisis: {res.critical_analysis}")
    print(f"Aprobación: {'Aprobado ✅' if res.final_passed else 'Reprobado ❌'}")
    print(f"===================================")

if __name__ == "__main__":
    import asyncio
    asyncio.run(run_sample_evaluation())
