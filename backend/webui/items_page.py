"""Items tab: the original demo CRUD resource, in pure-Python UI."""

from __future__ import annotations

from nicegui import ui

from backend.routers.items import (
    ItemCreate,
    create_item,
    delete_item,
    list_items,
)

from .common import card, header, page_body, page_intro


@ui.page("/items")
def items_page() -> None:
    header("/items")

    name = {"value": ""}
    desc = {"value": ""}

    with page_body():
        page_intro("Items", "The original demo CRUD resource, backed by the same API.")

        with ui.row().classes("w-full gap-4 items-start"):
            with card("New item", "add_box").classes("w-96"):
                ui.input("Name").props("outlined dense").classes("w-full").bind_value(
                    name, "value"
                )
                ui.input("Description").props("outlined dense").classes(
                    "w-full"
                ).bind_value(desc, "value")

                def add() -> None:
                    if not name["value"].strip():
                        ui.notify("Name is required", type="warning")
                        return
                    create_item(
                        ItemCreate(name=name["value"], description=desc["value"])
                    )
                    name["value"] = ""
                    desc["value"] = ""
                    table.refresh()

                ui.button("Add item", icon="add", on_click=add).classes("w-full mt-2")

            with ui.column().classes("flex-grow gap-2 min-w-[320px]"):

                @ui.refreshable
                def table() -> None:
                    items = list_items()
                    if not items:
                        ui.label("No items yet.").classes("text-slate-500")
                        return
                    for item in items:
                        with card().classes("w-full"):
                            row_cls = "items-center justify-between w-full"
                            with ui.row().classes(row_cls):
                                with ui.column().classes("gap-0"):
                                    ui.label(item.name).classes("font-semibold")
                                    ui.label(item.description).classes(
                                        "text-sm text-slate-500"
                                    )
                                ui.button(
                                    icon="delete",
                                    on_click=lambda i=item.id: _delete(i),
                                ).props("flat color=red dense")

                def _delete(item_id: int) -> None:
                    delete_item(item_id)
                    table.refresh()

                table()
