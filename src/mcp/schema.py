# Placeholder for MCP JSON-RPC schema validation 

from typing import Any, Dict
from src.mcp.error import JsonRpcError, INVALID_REQUEST

def validate_jsonrpc_request(data: Dict[str, Any]) -> None:
    if not isinstance(data, dict):
        raise JsonRpcError(INVALID_REQUEST, "Request must be a JSON object")
    if data.get("jsonrpc") != "2.0":
        raise JsonRpcError(INVALID_REQUEST, "jsonrpc version must be '2.0'")
    if "method" not in data or not isinstance(data["method"], str):
        raise JsonRpcError(INVALID_REQUEST, "Missing or invalid 'method'")
    if "id" not in data:
        raise JsonRpcError(INVALID_REQUEST, "Missing 'id'")
    # params is optional, but if present must be dict or list
    if "params" in data and not isinstance(data["params"], (dict, list)):
        raise JsonRpcError(INVALID_REQUEST, "'params' must be an object or array if present") 