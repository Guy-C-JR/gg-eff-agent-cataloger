from toolkit import ToolRegistry, tool


@tool("fetch_fhir_patient")
def fetch_patient(patient_id: str) -> dict:
    return {"id": patient_id}


ToolRegistry.register("query_ehr_db", lambda q: q)
ToolRegistry.register("unknown_debug_tool", lambda x: x)

AGENT_TOOLS = ["fetch_fhir_patient", "query_ehr_db"]
