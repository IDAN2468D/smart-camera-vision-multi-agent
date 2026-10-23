import json
import logging
from typing import Dict, Any, List
from dal.detection_repo import detection_repo
from config.settings import settings

logger = logging.getLogger(__name__)

class VisionMCPServerService:
    """Model Context Protocol (MCP) JSON-RPC 2.0 Server Service.
    
    Implements the standard MCP specification highlighted in the course syllabus (Pages 16-17, 20, 22):
    - Allows Claude, Cursor, AI Agents, and external LLM clients to discover and invoke Vision AI tools
    - Provides real-time camera state, historical visual memory RAG, and commerce lookup
    """

    SERVER_NAME = "vision-agent-mcp-server"
    SERVER_VERSION = "2.0.0"

    def get_capabilities(self) -> Dict[str, Any]:
        """Return MCP server initialization metadata and supported capabilities."""
        return {
            "protocolVersion": "2024-11-05",
            "serverInfo": {
                "name": self.SERVER_NAME,
                "version": self.SERVER_VERSION
            },
            "capabilities": {
                "tools": {
                    "listChanged": False
                },
                "resources": {
                    "subscribe": False,
                    "listChanged": False
                }
            }
        }

    def list_tools(self) -> List[Dict[str, Any]]:
        """List all callable tools available through the Vision MCP server."""
        return [
            {
                "name": "get_latest_detection",
                "description": "Retrieve the most recent camera recognition record including detected objects, OCR text, and Hebrew knowledge enrichment.",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "search_visual_memory",
                "description": "Perform semantic or keyword memory search across previous detections stored in MongoDB Atlas.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Object name or entity to search (e.g. 'Smartphone', 'Human Face', 'Apple')"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of records to return (default 5)",
                            "default": 5
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "get_system_telemetry",
                "description": "Get real-time operational metrics: active model ID, database status, and feature flags.",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            }
        ]

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool invoked by an MCP client."""
        logger.info(f"[MCP] Executing tool: '{tool_name}' with args: {arguments}")

        if tool_name == "get_latest_detection":
            recent = detection_repo.get_recent_detections(limit=1)
            if not recent:
                return {
                    "content": [{"type": "text", "text": "No detections currently recorded in MongoDB Atlas."}]
                }
            latest = recent[0]
            # Strip large binary thumbnail/audio for clean LLM context
            summary = {
                "object_name": latest.get("object_name"),
                "category": latest.get("category"),
                "confidence": latest.get("confidence"),
                "detected_entities": latest.get("detected_entities"),
                "detected_text": latest.get("detected_text"),
                "enrichment_summary": latest.get("enrichment_summary"),
                "product_info": latest.get("product_info"),
                "timestamp": latest.get("timestamp")
            }
            return {
                "content": [{"type": "text", "text": json.dumps(summary, ensure_ascii=False, indent=2)}]
            }

        elif tool_name == "search_visual_memory":
            q = arguments.get("query", "")
            limit = arguments.get("limit", 5)
            matches = detection_repo.find_by_object_name(object_name=q, limit=limit)
            clean_matches = []
            for m in matches:
                clean_matches.append({
                    "object_name": m.get("object_name"),
                    "category": m.get("category"),
                    "confidence": m.get("confidence"),
                    "timestamp": m.get("timestamp"),
                    "description": m.get("visual_description")
                })
            return {
                "content": [{"type": "text", "text": json.dumps(clean_matches, ensure_ascii=False, indent=2)}]
            }

        elif tool_name == "get_system_telemetry":
            db_ok = detection_repo.ping()
            telemetry = {
                "server": self.SERVER_NAME,
                "version": self.SERVER_VERSION,
                "active_model": settings.MODEL_ID,
                "database_connected": db_ok,
                "collection": detection_repo.collection_name,
                "database": detection_repo.db_name
            }
            return {
                "content": [{"type": "text", "text": json.dumps(telemetry, ensure_ascii=False, indent=2)}]
            }

        else:
            return {
                "isError": True,
                "content": [{"type": "text", "text": f"Tool '{tool_name}' not found on this MCP server."}]
            }

    def handle_json_rpc(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming JSON-RPC 2.0 MCP request."""
        req_id = request_data.get("id")
        method = request_data.get("method")
        params = request_data.get("params", {})

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": self.get_capabilities()
            }
        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"tools": self.list_tools()}
            }
        elif method == "tools/call":
            tool_name = params.get("name")
            args = params.get("arguments", {})
            result = self.call_tool(tool_name, args)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": result
            }
        elif method == "ping":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {}
            }
        else:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": -32601,
                    "message": f"Method '{method}' not implemented."
                }
            }

# Singleton service instance
mcp_server_service = VisionMCPServerService()
