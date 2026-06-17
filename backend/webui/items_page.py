"""Items tab: the original demo CRUD resource, in pure-Python UI."""

from __future__ import annotations

from nicegui import ui

from backend.routers.items import (
    ItemCreate,
    create_item,
    delete_item,
    list_items,
)

from .common import header, page_intro


@ui.page("/items")
def items_page() -> None:
    header("/items")
    page_intro("Items", "The original demo CRUD resource, backed by the same API.")

    name = {"value": ""}
    desc = {"value": ""}

    with ui.row().classes("w-full gap-4 no-wrap items-start"):
        with ui.card().classes("w-96"):
            ui.label("New item").classes("font-semibold")
            ui.input("Name").classes("w-full").bind_value(name, "value")
            ui.input("Description").classes("w-full").bind_value(desc, "value")

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

            ui.button("Add item", on_click=add).classes("w-full mt-2")

        with ui.column().classes("flex-grow"):

            @ui.refreshable
            def table() -> None:
                items = list_items()
                if not items:
                    ui.label("No items yet.").classes("text-slate-500")
                    return
                for item in items:
                    with ui.card().classes("w-full"):
                        with ui.row().classes("items-center justify-between w-full"):
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
