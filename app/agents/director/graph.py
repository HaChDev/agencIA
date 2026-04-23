"""
AgencIA - Grafo del Director (Workflow Reflexivo)
=================================================
Grafo LangGraph con loops de retroalimentación crítica.

Arquitectura de tokens:
- messages es SOLO para diálogo ligero.
- Los datos de research viven en campos estructurados del estado.
- Cada nodo construye su contexto mínimo para no exceder el TPM.
"""

from typing import Dict, Any, List, Literal
import json
import re

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage, RemoveMessage
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from app.core.config import settings
from app.agents.director.state import DirectorState, AgentPhase, StrategyVersion, ReviewComment
from app.agents.director.prompts import (
    DIRECTOR_SYSTEM_PROMPT,
    ANALYZE_BRIEF_PROMPT,
    RESEARCH_EXECUTION_PROMPT,
    DRAFT_STRATEGY_PROMPT,
    CRITIQUE_STRATEGY_PROMPT,
    REFINE_STRATEGY_PROMPT,
    DECOMPOSE_TASKS_PROMPT
)
from app.agents.director.tools import get_director_tools

# Constante global del límite de iteraciones de investigación
MAX_RESEARCH_ITERATIONS = 3

# ============================================
# UTILS
# ============================================
def get_llm():
    """Retorna instancia del LLM principal."""
    return ChatGroq(
        api_key=settings.GROQ_API_KEY,
        model=settings.LLM_MODEL_PRIMARY,
        temperature=settings.LLM_TEMPERATURE_PRI
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


def deep_merge(base: Dict, override: Dict) -> Dict:
    """
    Merge profundo de dos diccionarios.
    Las listas se concatenan (sin duplicados), los dicts se mergean recursivamente.
    """
    merged = base.copy()
    for key, value in override.items():
        if key in merged:
            if isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key] = deep_merge(merged[key], value)
            elif isinstance(merged[key], list) and isinstance(value, list):
                # Concatenar sin duplicados
                existing_set = {json.dumps(item, sort_keys=True, ensure_ascii=False) if isinstance(item, dict) else str(item) for item in merged[key]}
                for item in value:
                    item_key = json.dumps(item, sort_keys=True, ensure_ascii=False) if isinstance(item, dict) else str(item)
                    if item_key not in existing_set:
                        merged[key].append(item)
            else:
                merged[key] = value
        else:
            merged[key] = value
    return merged


def extract_findings_from_tool_messages(messages: List) -> Dict[str, Any]:
    """
    Extrae datos relevantes de los ToolMessages de forma DETERMINISTA (sin LLM).
    Parsea el contenido semi-estructurado que devuelven nuestras herramientas.

    Returns:
        Dict con claves: market_data, benchmarks, trends, key_insights, sources
    """
    findings: Dict[str, Any] = {
        "market_data": {},
        "benchmarks": {},
        "trends": [],
        "competitors": [],
        "key_insights": [],
        "sources": [],
        "raw_summaries": []
    }

    for msg in messages:
        if not isinstance(msg, ToolMessage):
            continue

        content = msg.content or ""

        # Saltar resultados vacíos o sin información
        if not content or "No se encontró" in content or "Error" in content:
            continue

        # Truncar contenido individual a 1500 chars para mantener control
        content_truncated = content[:1500]

        # Extraer fuentes mencionadas
        source_matches = re.findall(r'Fuente:\s*(.+)', content)
        for src in source_matches:
            source_clean = src.strip()
            if source_clean and source_clean not in findings["sources"]:
                findings["sources"].append(source_clean)

        # Extraer URLs de fuentes externas
        url_matches = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', content)
        for title, url in url_matches:
            source_entry = f"{title.strip()} ({url.strip()})"
            if source_entry not in findings["sources"]:
                findings["sources"].append(source_entry)

        # Extraer benchmarks si vienen de get_channel_benchmarks
        if "Benchmarks" in content or "benchmark" in content.lower():
            # Intentar parsear JSON embebido
            json_match = re.search(r'\{[^{}]+\}', content)
            if json_match:
                try:
                    bench_data = json.loads(json_match.group())
                    findings["benchmarks"] = deep_merge(findings["benchmarks"], bench_data)
                except json.JSONDecodeError:
                    pass

        # Extraer datos de mercado (secciones con ** o ### encabezados)
        market_sections = re.findall(r'\*\*(.+?)\*\*[:\s]*(.+?)(?=\n\*\*|\n###|\Z)', content, re.DOTALL)
        for section_title, section_content in market_sections[:5]:
            key = section_title.strip().lower().replace(" ", "_")[:50]
            value = section_content.strip()[:300]
            if key and value and key not in findings["market_data"]:
                findings["market_data"][key] = value

        # Guardar un resumen truncado del contenido bruto
        summary_line = content_truncated.split('\n')[0].strip()[:200]
        if summary_line and summary_line not in findings["raw_summaries"]:
            findings["raw_summaries"].append(summary_line)

    # Limitar raw_summaries a los 5 más recientes
    findings["raw_summaries"] = findings["raw_summaries"][-5:]

    return findings


# ============================================
# NODES
# ============================================

async def analyze_brief(state: DirectorState):
    """
    Fase 1: Diagnóstico inicial del brief.
    Guarda el análisis en initial_analysis (campo estructurado, NO en messages acumulativos).
    """
    llm = get_llm()
    brief = state["client_brief"]

    msg = HumanMessage(content=ANALYZE_BRIEF_PROMPT.format(
        client_name=state["client_id"],
        brief_context=str(brief)
    ))

    response = await llm.ainvoke([SystemMessage(content=DIRECTOR_SYSTEM_PROMPT), msg])
    analysis_json = parse_json_output(response.content)

    return {
        "messages": [response],
        "initial_analysis": analysis_json,
        "current_phase": AgentPhase.DIAGNOSTIC_RESEARCH.value
    }


async def research_execution(state: DirectorState):
    """
    Fase 2: Ejecución de investigación usando Tools.

    Principios:
    - Construye prompt INFORMADO de lo que ya sabe (research_findings).
    - Evita repetir queries ya intentadas (research_queries_attempted).
    - Pasa SOLO los últimos mensajes al LLM, no todo el historial.
    - Límite duro de MAX_RESEARCH_ITERATIONS.
    """
    llm = get_llm()
    tools = get_director_tools()
    llm_with_tools = llm.bind_tools(tools)

    analysis = state.get("initial_analysis", {})
    recommended_topics = analysis.get("recommended_research_topics", [])
    iteration = state.get("research_iterations", 0)
    findings = state.get("research_findings", {})
    queries_attempted = state.get("research_queries_attempted", [])

    # Salida forzada si alcanzamos el límite
    if iteration >= MAX_RESEARCH_ITERATIONS:
        return {"current_phase": AgentPhase.DRAFTING_STRATEGY.value}

    # Construir sección de hallazgos previos
    already_known_section = ""
    if findings and any(findings.get(k) for k in ["market_data", "benchmarks", "trends", "sources"]):
        known_parts = []
        if findings.get("market_data"):
            known_parts.append(f"- Datos de mercado: {list(findings['market_data'].keys())[:5]}")
        if findings.get("benchmarks"):
            known_parts.append(f"- Benchmarks: {list(findings['benchmarks'].keys())[:5]}")
        if findings.get("trends"):
            known_parts.append(f"- Tendencias: {findings['trends'][:5]}")
        if findings.get("sources"):
            known_parts.append(f"- Fuentes consultadas: {len(findings['sources'])}")
        already_known_section = "INFORMACIÓN YA OBTENIDA (NO buscar de nuevo):\n" + "\n".join(known_parts)

    # Construir sección de queries ya intentadas
    queries_done_section = ""
    if queries_attempted:
        queries_done_section = "QUERIES YA INTENTADAS (NO repetir):\n" + "\n".join(
            f"- {q}" for q in queries_attempted[-10:]
        )

    prompt = RESEARCH_EXECUTION_PROMPT.format(
        analysis=json.dumps(analysis, ensure_ascii=False)[:500],
        recommended_topics=", ".join(recommended_topics) if recommended_topics else "No especificados",
        current_iteration=iteration + 1,
        max_iterations=MAX_RESEARCH_ITERATIONS,
        already_known_section=already_known_section,
        queries_done_section=queries_done_section
    )

    # Solo pasamos los últimos 3 mensajes + el prompt nuevo para controlar tokens
    recent_messages = state["messages"][-3:] if len(state["messages"]) > 3 else state["messages"]
    response = await llm_with_tools.ainvoke(
        [SystemMessage(content=DIRECTOR_SYSTEM_PROMPT)] + recent_messages + [HumanMessage(content=prompt)]
    )

    # Registrar las queries que el LLM intentó en esta iteración
    new_queries = []
    if hasattr(response, 'tool_calls') and response.tool_calls:
        for tc in response.tool_calls:
            query_text = tc.get("args", {}).get("query", "") or str(tc.get("args", {}))
            new_queries.append(query_text[:100])

    return {
        "messages": [response],
        "research_iterations": iteration + 1,
        "research_queries_attempted": queries_attempted + new_queries,
    }


async def extract_findings(state: DirectorState):
    """
    Nodo intermedio: Extrae hallazgos de los ToolMessages de forma DETERMINISTA.

    Se ejecuta después de 'tools' y antes de volver a 'research_execution'.
    - Parsea los ToolMessages más recientes (Python puro, sin LLM).
    - Hace merge con research_findings existentes.
    - Limpia los ToolMessages del canal messages para evitar acumulación de tokens.
    """
    messages = state["messages"]
    existing_findings = state.get("research_findings", {})

    # Extraer findings de los ToolMessages recientes
    new_findings = extract_findings_from_tool_messages(messages)

    # Merge con findings existentes
    merged_findings = deep_merge(existing_findings, new_findings)

    # Limpiar ToolMessages y sus llamadas AIMessages del historial para evitar acumulación de tokens.
    messages_to_remove = []
    for msg in messages:
        if isinstance(msg, ToolMessage) or (isinstance(msg, AIMessage) and getattr(msg, "tool_calls", None)):
            messages_to_remove.append(RemoveMessage(id=msg.id))

    return {
        "messages": messages_to_remove,
        "research_findings": merged_findings,
    }


async def draft_strategy(state: DirectorState):
    """
    Fase 3: Generación del primer borrador.
    Usa SOLO datos estructurados (brief + findings), NO el historial de messages.
    """
    llm = get_llm()

    brief = state.get("client_brief", {})
    findings = state.get("research_findings", {})

    # Construir resumen de findings para el prompt
    findings_parts = []
    if findings.get("market_data"):
        findings_parts.append("### Datos de Mercado")
        for k, v in list(findings["market_data"].items())[:5]:
            findings_parts.append(f"- {k}: {str(v)[:150]}")

    if findings.get("benchmarks"):
        findings_parts.append("### Benchmarks")
        for k, v in list(findings["benchmarks"].items())[:5]:
            findings_parts.append(f"- {k}: {v}")

    if findings.get("trends"):
        findings_parts.append("### Tendencias")
        for t in findings["trends"][:5]:
            findings_parts.append(f"- {t}")

    if findings.get("raw_summaries"):
        findings_parts.append("### Resúmenes de Investigación")
        for s in findings["raw_summaries"][:3]:
            findings_parts.append(f"- {s}")

    findings_summary = "\n".join(findings_parts) if findings_parts else "No se encontraron hallazgos de investigación relevantes."
    brief_summary = json.dumps(brief, indent=2, ensure_ascii=False)[:600] if brief else "Brief no disponible."

    msg = HumanMessage(content=DRAFT_STRATEGY_PROMPT.format(
        brief_summary=brief_summary,
        findings_summary=findings_summary
    ))

    # Contexto mínimo: solo system + prompt, sin historial
    response = await llm.ainvoke([SystemMessage(content=DIRECTOR_SYSTEM_PROMPT), msg])

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
    """
    Fase 4: El Abogado del Diablo.
    Ya usa contexto mínimo (system + estrategia actual).
    """
    llm = get_llm()

    current_strat = state["current_strategy"]

    msg = HumanMessage(content=CRITIQUE_STRATEGY_PROMPT.format(
        current_strategy=json.dumps(current_strat, indent=2, ensure_ascii=False)[:2000]
    ))

    response = await llm.ainvoke([SystemMessage(content=DIRECTOR_SYSTEM_PROMPT), msg])

    critique_text = response.content

    # Heurística simple: Si el texto contiene "APROBADO" o similar
    approved = "APROBADO" in critique_text.upper() or "NO HAY CAMBIOS" in critique_text.upper()

    if approved or state["iteration_count"] >= 2:  # Máximo 2 iteraciones de mejora
        next_phase = AgentPhase.DECOMPOSING_TASKS.value
    else:
        next_phase = AgentPhase.REFINING_STRATEGY.value

    return {
        "messages": [response],
        "current_critique": critique_text,
        "current_phase": next_phase,
        "iteration_count": state["iteration_count"] + 1
    }


async def refine_strategy(state: DirectorState):
    """
    Fase 4b: Refinamiento basado en crítica.
    Usa SOLO strategy + critique, NO el historial completo de messages.
    """
    llm = get_llm()

    current_strat = state.get("current_strategy", {})
    critique = state.get("current_critique", "Sin crítica disponible.")

    msg = HumanMessage(content=REFINE_STRATEGY_PROMPT.format(
        current_strategy=json.dumps(current_strat, indent=2, ensure_ascii=False)[:2000],
        critique=str(critique)[:1000]
    ))

    # Contexto mínimo: solo system + prompt
    response = await llm.ainvoke([SystemMessage(content=DIRECTOR_SYSTEM_PROMPT), msg])
    new_strategy = parse_json_output(response.content)

    new_version = StrategyVersion(
        version_number=len(state["strategy_versions"]) + 1,
        content=new_strategy
    )

    return {
        "messages": [response],
        "current_strategy": new_strategy,
        "strategy_versions": [new_version],
        "current_phase": AgentPhase.CRITIQUING_STRATEGY.value  # Volver a criticar
    }


async def decompose_tasks(state: DirectorState):
    """
    Fase 5: Plan Operativo.
    Usa SOLO la estrategia aprobada, NO el historial de messages.
    """
    llm = get_llm()

    strategy = state.get("current_strategy", {})

    msg = HumanMessage(content=DECOMPOSE_TASKS_PROMPT.format(
        strategy=json.dumps(strategy, indent=2, ensure_ascii=False)[:2000]
    ))

    # Contexto mínimo: solo system + prompt
    response = await llm.ainvoke([SystemMessage(content=DIRECTOR_SYSTEM_PROMPT), msg])

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
    builder.add_node("extract_findings", extract_findings)
    builder.add_node("draft_strategy", draft_strategy)
    builder.add_node("critique_strategy", critique_strategy)
    builder.add_node("refine_strategy", refine_strategy)
    builder.add_node("decompose_tasks", decompose_tasks)

    # Tool Node (prebuilt)
    tool_node = ToolNode(get_director_tools())
    builder.add_node("tools", tool_node)

    # === EDGES ===
    builder.set_entry_point("analyze_brief")
    builder.add_edge("analyze_brief", "research_execution")

    # Lógica condicional de investigación
    def should_continue_research(state: DirectorState):
        """Decide si seguir investigando o pasar a drafting."""
        # Prioridad 1: Si la fase fue cambiada a DRAFTING (por límite de iteraciones)
        if state.get("current_phase") == AgentPhase.DRAFTING_STRATEGY.value:
            return "draft_strategy"

        # Prioridad 2: Si el LLM pidió herramientas
        last_msg = state["messages"][-1] if state["messages"] else None
        if last_msg and isinstance(last_msg, AIMessage) and getattr(last_msg, "tool_calls", None):
            return "tools"

        # Default: investigación completa, pasar a drafting
        return "draft_strategy"

    builder.add_conditional_edges("research_execution", should_continue_research)

    # Después de tools → extract_findings → research_execution (loop controlado)
    builder.add_edge("tools", "extract_findings")
    builder.add_edge("extract_findings", "research_execution")

    builder.add_edge("draft_strategy", "critique_strategy")

    def critique_router(state: DirectorState):
        """Decide si la estrategia necesita refinamiento o está lista."""
        if state["current_phase"] == AgentPhase.DECOMPOSING_TASKS.value:
            return "decompose_tasks"
        return "refine_strategy"

    builder.add_conditional_edges("critique_strategy", critique_router)
    builder.add_edge("refine_strategy", "critique_strategy")  # Loop de mejora

    builder.add_edge("decompose_tasks", END)

    return builder.compile()

# Singleton
_graph = None
def get_director_graph():
    global _graph
    if _graph is None:
        _graph = create_director_graph()
    return _graph
