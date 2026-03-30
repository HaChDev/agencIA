"""
AgencIA - Grafo del Director (Workflow Reflexivo)
=================================================
Grafo LangGraph con loops de retroalimentación crítica.
"""

from typing import Dict, Any, Literal
import json

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from app.core.config import settings
from app.agents.director.state import DirectorState, AgentPhase, StrategyVersion, ReviewComment
from app.agents.director.prompts import (
    DIRECTOR_SYSTEM_PROMPT,
    ANALYZE_BRIEF_PROMPT,
    DRAFT_STRATEGY_PROMPT,
    CRITIQUE_STRATEGY_PROMPT,
    DECOMPOSE_TASKS_PROMPT
)
from app.agents.director.tools import get_director_tools

# ============================================
# UTILS
# ============================================
def get_llm():
    return ChatGroq(
        api_key=settings.GROQ_API_KEY,
        model=settings.LLM_MODEL_PRIMARY,
        temperature=0.2 # Baja temperatura para razonamiento
    )

def parse_json_output(content: str) -> Dict:
    """Intenta parsear JSON robustamente."""
    content = content.strip()
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0]
    elif "```" in content:
        content = content.split("```")[1].split("```")[0]
    
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {"raw_content": content, "error": "Failed to parse JSON"}

# ============================================
# NODES
# ============================================

async def analyze_brief(state: DirectorState):
    """Fase 1: Diagnóstico inicial."""
    llm = get_llm()
    brief = state["client_brief"]
    
    msg = HumanMessage(content=ANALYZE_BRIEF_PROMPT.format(
        client_name=state["client_id"],
        brief_context=str(brief)
    ))
    
    response = await llm.ainvoke([SystemMessage(DIRECTOR_SYSTEM_PROMPT), msg])
    analysis_json = parse_json_output(response.content)
    
    # Decidir si necesitamos investigar más
    next_phase = AgentPhase.DIAGNOSTIC_RESEARCH.value
    
    # Si la viabilidad es muy baja, podríamos abortar, pero por ahora seguimos investigando
    
    return {
        "messages": [response],
        "research_data": {"initial_analysis": analysis_json},
        "current_phase": next_phase
    }

async def research_execution(state: DirectorState):
    """
    Fase 2: Ejecución de investigación usando Tools.
    Este nodo decide qué herramientas llamar basado en el análisis inicial.
    """
    llm = get_llm()
    tools = get_director_tools()
    llm_with_tools = llm.bind_tools(tools)
    
    analysis = state["research_data"].get("initial_analysis", {})
    recommended_topics = analysis.get("recommended_research_topics", [])
    
    # Si ya tenemos research suficiente, pasamos a drafting
    # (Simplificación: si ya ejecutamos tools una vez, seguimos)
    last_msg = state["messages"][-1]
    if isinstance(last_msg, AIMessage) and not last_msg.tool_calls and "tool_output" in str(state["messages"][-2]):
         return {"current_phase": AgentPhase.DRAFTING_STRATEGY.value}
         
    prompt = f"""
    Basado en el análisis inicial: {analysis}
    
    Ejecuta las herramientas necesarias para investigar estos temas: {recommended_topics}.
    Usa 'search_knowledge_base' para teoría y 'market_intelligence' para datos externos actualizados.
    """
    
    response = await llm_with_tools.ainvoke(
        state["messages"] + [HumanMessage(content=prompt)]
    )
    
    return {"messages": [response]}


async def draft_strategy(state: DirectorState):
    """Fase 3: Generación del primer borrador."""
    llm = get_llm()
    
    # Resumir research (podría ser un nodo separado si es muy largo)
    research_summary = str(state["research_data"]) 
    
    msg = HumanMessage(content=DRAFT_STRATEGY_PROMPT.format(
        research_summary=research_summary
    ))
    
    response = await llm.ainvoke(state["messages"] + [msg])
    
    strategy_content = parse_json_output(response.content)
    
    new_version = StrategyVersion(
        version_number=len(state["strategy_versions"]) + 1,
        content=strategy_content
    )
    
    return {
        "messages": [response],
        "current_strategy": strategy_content,
        "strategy_versions": [new_version],
        "current_phase": AgentPhase.CRITIQUING_STRATEGY.value
    }


async def critique_strategy(state: DirectorState):
    """Fase 4: El Abogado del Diablo."""
    llm = get_llm()
    
    current_strat = state["current_strategy"]
    
    msg = HumanMessage(content=CRITIQUE_STRATEGY_PROMPT.format(
        current_strategy=json.dumps(current_strat, indent=2)
    ))
    
    response = await llm.ainvoke([SystemMessage(DIRECTOR_SYSTEM_PROMPT), msg])
    
    critique_text = response.content
    
    # Heurística simple: Si el texto contiene "APROBADO" o similar
    approved = "APROBADO" in critique_text.upper() or "NO HAY CAMBIOS" in critique_text.upper()
    
    if approved or state["iteration_count"] >= 2: # Máximo 2 iteraciones de mejora
        next_phase = AgentPhase.DECOMPOSING_TASKS.value
    else:
        next_phase = AgentPhase.REFINING_STRATEGY.value
        
    return {
        "messages": [response],
        "current_critique": critique_text, # Simplificado, podría ser lista
        "current_phase": next_phase,
        "iteration_count": state["iteration_count"] + 1
    }

async def refine_strategy(state: DirectorState):
    """Fase 4b: Refinamiento basado en crítica."""
    llm = get_llm()
    
    prompt = f"""
    Crítica recibida: {state['current_critique']}
    
    Por favor REESCRIBE la estrategia abordando estos puntos críticos.
    Mantén el formato JSON.
    """
    
    response = await llm.ainvoke(state["messages"] + [HumanMessage(content=prompt)])
    new_strategy = parse_json_output(response.content)
    
    # Actualizar versión
    new_version = StrategyVersion(
        version_number=len(state["strategy_versions"]) + 1,
        content=new_strategy
    )
    
    return {
        "messages": [response],
        "current_strategy": new_strategy,
        "strategy_versions": [new_version],
        "current_phase": AgentPhase.CRITIQUING_STRATEGY.value # Volver a criticar
    }

async def decompose_tasks(state: DirectorState):
    """Fase 5: Plan Operativo."""
    llm = get_llm()
    
    msg = HumanMessage(content=DECOMPOSE_TASKS_PROMPT)
    response = await llm.ainvoke(state["messages"] + [msg])
    
    tasks_json = parse_json_output(response.content)
    # Asumimos que tasks_json es una lista o tiene una clave "tasks"
    tasks = tasks_json.get("tasks", []) if isinstance(tasks_json, dict) else tasks_json
    
    return {
        "messages": [response],
        "tasks": tasks,
        "current_phase": AgentPhase.COMPLETED.value
    }


# ============================================
# GRAPH DEFINITION
# ============================================

def create_director_graph():
    builder = StateGraph(DirectorState)
    
    # Nodos principales
    builder.add_node("analyze_brief", analyze_brief)
    builder.add_node("research_execution", research_execution)
    builder.add_node("draft_strategy", draft_strategy)
    builder.add_node("critique_strategy", critique_strategy)
    builder.add_node("refine_strategy", refine_strategy)
    builder.add_node("decompose_tasks", decompose_tasks)
    
    # Tool Node (prebuilt)
    tool_node = ToolNode(get_director_tools())
    builder.add_node("tools", tool_node)
    
    # Edges
    builder.set_entry_point("analyze_brief")
    builder.add_edge("analyze_brief", "research_execution")
    
    # Lógica condicional investigación
    def should_continue_research(state: DirectorState):
        last_msg = state["messages"][-1]
        if isinstance(last_msg, AIMessage) and last_msg.tool_calls:
            return "tools"
        if state["current_phase"] == AgentPhase.DRAFTING_STRATEGY.value:
            return "draft_strategy"
        return "draft_strategy" # Default fallback
        
    builder.add_conditional_edges("research_execution", should_continue_research)
    builder.add_edge("tools", "research_execution") # Loop back after tool execution
    
    builder.add_edge("draft_strategy", "critique_strategy")
    
    def critique_router(state: DirectorState):
        if state["current_phase"] == AgentPhase.DECOMPOSING_TASKS.value:
            return "decompose_tasks"
        return "refine_strategy"
        
    builder.add_conditional_edges("critique_strategy", critique_router)
    builder.add_edge("refine_strategy", "critique_strategy") # Loop de mejora
    
    builder.add_edge("decompose_tasks", END)
    
    return builder.compile()

# Singleton
_graph = None
def get_director_graph():
    global _graph
    if _graph is None:
        _graph = create_director_graph()
    return _graph
