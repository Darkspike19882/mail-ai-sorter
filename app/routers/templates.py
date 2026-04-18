from fastapi import APIRouter

router = APIRouter(tags=["templates"])


@router.get("/api/templates")
async def api_templates():
    import memory
    return {"success": True, "templates": memory.get_templates()}


@router.post("/api/templates")
async def api_create_template():
    return {"success": False, "error": "Not migrated yet"}


@router.put("/api/templates/{template_id}")
async def api_update_template(template_id: int):
    return {"success": False, "error": "Not migrated yet"}


@router.delete("/api/templates/{template_id}")
async def api_delete_template(template_id: int):
    return {"success": False, "error": "Not migrated yet"}
